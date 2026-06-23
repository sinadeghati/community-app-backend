from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from korook_admin.audit import log_admin_action
from listings.models import ListingImage
from korook_platform.models import Event

from .mixins import AdminAPIMixin
from .pagination import AdminPageNumberPagination
from .serializers import ListingImageAdminSerializer


class AdminMediaListView(AdminAPIMixin, APIView):
    def get(self, request):
        qs = ListingImage.objects.select_related("listing").order_by("-uploaded_at")
        media_status = request.query_params.get("media_status", "pending_review")
        if media_status:
            qs = qs.filter(media_status=media_status)
        paginator = AdminPageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            ListingImageAdminSerializer(page, many=True, context={"request": request}).data
        )


class AdminMediaActionView(AdminAPIMixin, APIView):
    def post(self, request, media_id, action):
        image = ListingImage.objects.filter(pk=media_id).first()
        if not image:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if action == "approve":
            image.media_status = ListingImage.MediaStatus.ACTIVE
        elif action == "reject":
            image.media_status = ListingImage.MediaStatus.REJECTED
            image.moderation_reason = request.data.get("moderation_reason", "")
        elif action == "hide":
            image.media_status = ListingImage.MediaStatus.HIDDEN
        else:
            return Response({"detail": "Unknown action."}, status=status.HTTP_400_BAD_REQUEST)
        image.reviewed_by = request.user
        image.reviewed_at = timezone.now()
        image.save()
        log_admin_action(
            actor=request.user,
            action_type=f"media.{action}",
            object_type="listing_image",
            object_id=image.id,
            summary=f"Media {action} for listing {image.listing_id}",
        )
        return Response(
            ListingImageAdminSerializer(image, context={"request": request}).data
        )


class AdminEventCoverMediaView(AdminAPIMixin, APIView):
    def post(self, request, event_id, action):
        event = Event.objects.filter(pk=event_id).first()
        if not event:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if action == "approve-cover":
            event.cover_media_status = Event.MediaStatus.ACTIVE
        elif action == "reject-cover":
            event.cover_media_status = Event.MediaStatus.REJECTED
            event.cover_moderation_reason = request.data.get("moderation_reason", "")
        else:
            return Response({"detail": "Unknown action."}, status=status.HTTP_400_BAD_REQUEST)
        event.cover_reviewed_by = request.user
        event.cover_reviewed_at = timezone.now()
        event.save()
        return Response({"success": True, "cover_media_status": event.cover_media_status})
