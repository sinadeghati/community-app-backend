import os
import uuid

from django.core.files.storage import default_storage
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from korook_admin.audit import log_admin_action
from korook_platform.models import Event

from .event_admin_meta import (
    add_gallery_item,
    gallery_items,
    read_event_meta,
    remove_gallery_item,
    reorder_gallery,
)
from .image_validation import validate_image_upload
from .mixins import AdminAPIMixin


def _get_event(event_id):
    return Event.objects.filter(pk=event_id).first()


def _gallery_item_url(request, storage_path):
    if storage_path and default_storage.exists(storage_path):
        return request.build_absolute_uri(default_storage.url(storage_path))
    return None


def _serialize_media(event, request):
    cover_url = None
    if event.cover_image:
        cover_url = request.build_absolute_uri(event.cover_image.url)

    gallery = []
    for item in gallery_items(event):
        gallery.append(
            {
                **item,
                "image_url": _gallery_item_url(request, item.get("storage_path")),
            }
        )

    meta = read_event_meta(event)
    return {
        "cover_image_url": cover_url,
        "cover_media_status": event.cover_media_status,
        "cover_moderation_reason": event.cover_moderation_reason,
        "gallery": gallery,
        "media_count": (1 if cover_url else 0) + len(gallery),
        "tags": meta.get("tags", []),
        "contact": meta.get("contact", {}),
    }


class AdminEventMediaView(AdminAPIMixin, APIView):
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, event_id):
        event = _get_event(event_id)
        if not event:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(_serialize_media(event, request))

    def post(self, request, event_id):
        event = _get_event(event_id)
        if not event:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        role = (request.data.get("role") or "gallery").strip().lower()
        try:
            uploaded = validate_image_upload(request.data.get("image"))
        except ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

        if role == "cover":
            event.cover_image = uploaded
            event.cover_media_status = Event.MediaStatus.ACTIVE
            event.cover_moderation_reason = ""
            event.save(
                update_fields=[
                    "cover_image",
                    "cover_media_status",
                    "cover_moderation_reason",
                    "updated_at",
                ]
            )
            action = "event.cover.upload"
        else:
            extension = os.path.splitext(uploaded.name)[1].lower() or ".jpg"
            storage_path = default_storage.save(
                f"events/gallery/{event.id}/{uuid.uuid4().hex}{extension}",
                uploaded,
            )
            item = add_gallery_item(event, storage_path, uploaded.name)
            item["image_url"] = _gallery_item_url(request, storage_path)
            item["uploaded_at"] = timezone.now().isoformat()
            log_admin_action(
                actor=request.user,
                action_type="event.gallery.upload",
                object_type="event",
                object_id=event.id,
                summary=f"Uploaded gallery image for {event.title}",
            )
            return Response(item, status=status.HTTP_201_CREATED)

        log_admin_action(
            actor=request.user,
            action_type=action,
            object_type="event",
            object_id=event.id,
            summary=f"Uploaded cover image for {event.title}",
        )
        return Response(_serialize_media(event, request), status=status.HTTP_201_CREATED)


class AdminEventMediaReorderView(AdminAPIMixin, APIView):
    def post(self, request, event_id):
        event = _get_event(event_id)
        if not event:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        order = request.data.get("order")
        if not isinstance(order, list):
            return Response(
                {"order": ["Provide a list of gallery image IDs."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        reorder_gallery(event, [str(item) for item in order])
        log_admin_action(
            actor=request.user,
            action_type="event.gallery.reorder",
            object_type="event",
            object_id=event.id,
            summary=f"Reordered gallery for {event.title}",
        )
        return Response(_serialize_media(event, request))


class AdminEventMediaDetailView(AdminAPIMixin, APIView):
    parser_classes = [MultiPartParser, FormParser]

    def patch(self, request, event_id, image_id):
        event = _get_event(event_id)
        if not event:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if image_id == "cover":
            if "image" not in request.data or not request.data.get("image"):
                return Response(
                    {"image": ["Image file is required."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                uploaded = validate_image_upload(request.data.get("image"))
            except ValidationError as exc:
                return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)
            if event.cover_image:
                event.cover_image.delete(save=False)
            event.cover_image = uploaded
            event.cover_media_status = Event.MediaStatus.ACTIVE
            event.save(update_fields=["cover_image", "cover_media_status", "updated_at"])
            log_admin_action(
                actor=request.user,
                action_type="event.cover.replace",
                object_type="event",
                object_id=event.id,
                summary=f"Replaced cover for {event.title}",
            )
            return Response(_serialize_media(event, request))

        try:
            uploaded = validate_image_upload(request.data.get("image"))
        except ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

        gallery = gallery_items(event)
        target = next((item for item in gallery if item.get("id") == image_id), None)
        if not target:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        old_path = target.get("storage_path")
        extension = os.path.splitext(uploaded.name)[1].lower() or ".jpg"
        storage_path = default_storage.save(
            f"events/gallery/{event.id}/{uuid.uuid4().hex}{extension}",
            uploaded,
        )
        if old_path and default_storage.exists(old_path):
            default_storage.delete(old_path)

        from .event_admin_meta import read_event_meta, write_event_meta

        meta = read_event_meta(event)
        for item in meta["gallery"]:
            if item.get("id") == image_id:
                item["storage_path"] = storage_path
                item["filename"] = uploaded.name
                item["uploaded_at"] = timezone.now().isoformat()
        write_event_meta(event, meta)
        return Response(_serialize_media(event, request))

    def delete(self, request, event_id, image_id):
        event = _get_event(event_id)
        if not event:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if image_id == "cover":
            if event.cover_image:
                event.cover_image.delete(save=False)
                event.cover_image = None
                event.save(update_fields=["cover_image", "updated_at"])
            log_admin_action(
                actor=request.user,
                action_type="event.cover.delete",
                object_type="event",
                object_id=event.id,
                summary=f"Deleted cover for {event.title}",
            )
            return Response(status=status.HTTP_204_NO_CONTENT)

        removed = remove_gallery_item(event, image_id)
        if not removed:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        storage_path = removed.get("storage_path")
        if storage_path and default_storage.exists(storage_path):
            default_storage.delete(storage_path)
        log_admin_action(
            actor=request.user,
            action_type="event.gallery.delete",
            object_type="event",
            object_id=event.id,
            summary=f"Deleted gallery image for {event.title}",
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
