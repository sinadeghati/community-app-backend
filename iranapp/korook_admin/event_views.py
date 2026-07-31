from django.contrib.auth.models import User
from django.db.models import Q
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from korook_admin.audit import log_admin_action
from korook_platform.models import Event

from .mixins import AdminAPIMixin
from .pagination import AdminPageNumberPagination
from .serializers import EventAdminSerializer


class AdminEventListCreateView(AdminAPIMixin, APIView):
    def get(self, request):
        qs = Event.objects.select_related("owner", "listing").order_by("-starts_at")
        search = (request.query_params.get("search") or "").strip()
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(organizer__icontains=search))
        status_val = request.query_params.get("status")
        if status_val:
            qs = qs.filter(status=status_val)
        paginator = AdminPageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            EventAdminSerializer(page, many=True, context={"request": request}).data
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
        event = Event.objects.filter(pk=event_id).first()
        if not event:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(EventAdminSerializer(event, context={"request": request}).data)

    def patch(self, request, event_id):
        event = Event.objects.filter(pk=event_id).first()
        if not event:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
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
        elif action == "hide":
            event.status = Event.Status.HIDDEN
            event.save(update_fields=["status", "updated_at"])
        elif action == "feature":
            event.is_featured = bool(request.data.get("is_featured", True))
            event.save(update_fields=["is_featured", "updated_at"])
        elif action == "cover":
            event.cover_image = request.data.get("cover_image") or request.FILES.get("cover_image")
            event.save(update_fields=["cover_image", "updated_at"])
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
