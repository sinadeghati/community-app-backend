from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from korook_admin.audit import log_admin_action
from korook_platform.models import Event

from .mixins import AdminAPIMixin
from .pagination import AdminPageNumberPagination
from .serializers import EventAdminListSerializer, EventAdminSerializer


def _event_queryset():
    return Event.objects.select_related("owner", "listing").annotate(
        promotions_count=Count("promotions", distinct=True),
        reports_count=Count(
            "content_reports",
            distinct=True,
        ),
    )


def _filter_events(qs, request):
    search = (request.query_params.get("search") or "").strip()
    if search:
        qs = qs.filter(
            Q(title__icontains=search)
            | Q(organizer__icontains=search)
            | Q(city__icontains=search)
            | Q(listing__title__icontains=search)
            | Q(owner__username__icontains=search)
            | Q(owner__email__icontains=search)
        )

    status_val = request.query_params.get("status")
    if status_val:
        qs = qs.filter(status=status_val)

    category = (request.query_params.get("category") or "").strip()
    if category:
        qs = qs.filter(category__icontains=category)

    featured = request.query_params.get("featured")
    if featured in {"true", "false"}:
        qs = qs.filter(is_featured=(featured == "true"))

    starts_after = request.query_params.get("starts_after")
    if starts_after:
        qs = qs.filter(starts_at__date__gte=starts_after)

    starts_before = request.query_params.get("starts_before")
    if starts_before:
        qs = qs.filter(starts_at__date__lte=starts_before)

    ordering = request.query_params.get("ordering") or "-starts_at"
    allowed = {
        "starts_at",
        "-starts_at",
        "created_at",
        "-created_at",
        "title",
        "-title",
        "updated_at",
        "-updated_at",
    }
    if ordering in allowed:
        qs = qs.order_by(ordering)
    else:
        qs = qs.order_by("-starts_at")
    return qs


class AdminEventListCreateView(AdminAPIMixin, APIView):
    def get(self, request):
        qs = _filter_events(_event_queryset(), request)
        paginator = AdminPageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            EventAdminListSerializer(page, many=True, context={"request": request}).data
        )

    def post(self, request):
        owner_id = request.data.get("owner_id")
        if not owner_id:
            return Response({"detail": "owner_id required."}, status=status.HTTP_400_BAD_REQUEST)
        owner = User.objects.filter(pk=owner_id).first()
        if not owner:
            return Response({"detail": "Owner not found."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = EventAdminSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        event = serializer.save(owner=owner)
        log_admin_action(
            actor=request.user,
            action_type="event.create",
            object_type="event",
            object_id=event.id,
            summary=f"Created event {event.title}",
        )
        return Response(
            EventAdminSerializer(event, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class AdminEventDetailView(AdminAPIMixin, APIView):
    def get(self, request, event_id):
        event = _event_queryset().filter(pk=event_id).first()
        if not event:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(EventAdminSerializer(event, context={"request": request}).data)

    def patch(self, request, event_id):
        event = Event.objects.filter(pk=event_id).first()
        if not event:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        before = EventAdminSerializer(event, context={"request": request}).data
        serializer = EventAdminSerializer(
            event, data=request.data, partial=True, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        event = serializer.save()
        log_admin_action(
            actor=request.user,
            action_type="event.update",
            object_type="event",
            object_id=event.id,
            summary=f"Updated event {event.title}",
            before_state=before,
            after_state=EventAdminSerializer(event, context={"request": request}).data,
        )
        return Response(EventAdminSerializer(event, context={"request": request}).data)

    def delete(self, request, event_id):
        event = Event.objects.filter(pk=event_id).first()
        if not event:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        eid, title = event.id, event.title
        event.delete()
        log_admin_action(
            actor=request.user,
            action_type="event.delete",
            object_type="event",
            object_id=eid,
            summary=f"Deleted event {title}",
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminEventActionView(AdminAPIMixin, APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, event_id, action):
        event = Event.objects.filter(pk=event_id).first()
        if not event:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if action == "publish":
            event.status = Event.Status.PUBLISHED
            event.save(update_fields=["status", "updated_at"])
        elif action == "unpublish":
            event.status = Event.Status.DRAFT
            event.save(update_fields=["status", "updated_at"])
        elif action == "hide":
            event.status = Event.Status.HIDDEN
            event.save(update_fields=["status", "updated_at"])
        elif action == "archive":
            event.status = Event.Status.HIDDEN
            event.save(update_fields=["status", "updated_at"])
        elif action == "feature":
            event.is_featured = bool(request.data.get("is_featured", True))
            event.save(update_fields=["is_featured", "updated_at"])
        elif action == "unfeature":
            event.is_featured = False
            event.save(update_fields=["is_featured", "updated_at"])
        elif action == "cover":
            event.cover_image = request.data.get("cover_image") or request.FILES.get("cover_image")
            event.save(update_fields=["cover_image", "updated_at"])
        elif action == "duplicate":
            duplicate = Event.objects.create(
                title=f"Copy of {event.title}",
                description=event.description,
                category=event.category,
                starts_at=event.starts_at,
                ends_at=event.ends_at,
                location=event.location,
                address=event.address,
                city=event.city,
                state=event.state,
                zip_code=event.zip_code,
                country=event.country,
                latitude=event.latitude,
                longitude=event.longitude,
                organizer=event.organizer,
                ticket_url=event.ticket_url,
                ticket_provider_label=event.ticket_provider_label,
                listing=event.listing,
                owner=event.owner,
                status=Event.Status.DRAFT,
                is_featured=False,
                is_sponsored=event.is_sponsored,
                display_priority=event.display_priority,
                admin_note=event.admin_note,
            )
            log_admin_action(
                actor=request.user,
                action_type="event.duplicate",
                object_type="event",
                object_id=duplicate.id,
                summary=f"Duplicated event {event.title}",
            )
            return Response(
                EventAdminSerializer(duplicate, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response({"detail": "Unknown action."}, status=status.HTTP_400_BAD_REQUEST)

        log_admin_action(
            actor=request.user,
            action_type=f"event.{action}",
            object_type="event",
            object_id=event.id,
            summary=f"Event action {action} on {event.title}",
        )
        return Response(EventAdminSerializer(event, context={"request": request}).data)
