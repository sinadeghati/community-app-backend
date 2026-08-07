from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from korook_admin.audit import log_admin_action
from korook_platform.models import Promotion

from .mixins import AdminAPIMixin
from .pagination import AdminPageNumberPagination
from .serializers import PromotionAdminSerializer


class AdminPromotionListCreateView(AdminAPIMixin, APIView):
    def get(self, request):
        qs = Promotion.objects.select_related("listing", "event").order_by(
            "display_priority", "-created_at"
        )
        placement = request.query_params.get("placement")
        if placement:
            qs = qs.filter(placement=placement)
        status_val = request.query_params.get("status")
        if status_val:
            qs = qs.filter(status=status_val)
        event_id = request.query_params.get("event")
        if event_id:
            qs = qs.filter(event_id=event_id)
        paginator = AdminPageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            PromotionAdminSerializer(page, many=True, context={"request": request}).data
        )

    def post(self, request):
        serializer = PromotionAdminSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        promotion = serializer.save()
        promotion.refresh_status()
        log_admin_action(
            actor=request.user,
            action_type="promotion.create",
            object_type="promotion",
            object_id=promotion.id,
            summary=f"Created promotion {promotion.title}",
        )
        return Response(
            PromotionAdminSerializer(promotion, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class AdminPromotionDetailView(AdminAPIMixin, APIView):
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, promotion_id):
        promo = Promotion.objects.filter(pk=promotion_id).first()
        if not promo:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(PromotionAdminSerializer(promo, context={"request": request}).data)

    def patch(self, request, promotion_id):
        promo = Promotion.objects.filter(pk=promotion_id).first()
        if not promo:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = PromotionAdminSerializer(
            promo, data=request.data, partial=True, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        promo = serializer.save()
        promo.refresh_status()
        log_admin_action(
            actor=request.user,
            action_type="promotion.update",
            object_type="promotion",
            object_id=promo.id,
            summary=f"Updated promotion {promo.title}",
        )
        return Response(PromotionAdminSerializer(promo, context={"request": request}).data)

    def delete(self, request, promotion_id):
        promo = Promotion.objects.filter(pk=promotion_id).first()
        if not promo:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        pid, title = promo.id, promo.title
        promo.delete()
        log_admin_action(
            actor=request.user,
            action_type="promotion.delete",
            object_type="promotion",
            object_id=pid,
            summary=f"Deleted promotion {title}",
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminPromotionActionView(AdminAPIMixin, APIView):
    def post(self, request, promotion_id, action):
        promo = Promotion.objects.filter(pk=promotion_id).first()
        if not promo:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if action == "activate":
            promo.is_active = True
            promo.save(update_fields=["is_active", "updated_at"])
            promo.refresh_status()
        elif action == "pause":
            promo.is_active = False
            promo.status = Promotion.Status.PAUSED
            promo.save(update_fields=["is_active", "status", "updated_at"])
        else:
            return Response({"detail": "Unknown action."}, status=status.HTTP_400_BAD_REQUEST)
        log_admin_action(
            actor=request.user,
            action_type=f"promotion.{action}",
            object_type="promotion",
            object_id=promo.id,
            summary=f"Promotion {action} {promo.title}",
        )
        return Response(PromotionAdminSerializer(promo, context={"request": request}).data)
