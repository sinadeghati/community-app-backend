from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from korook_admin.audit import log_admin_action
from korook_platform.models import Promotion

from .mixins import AdminAPIMixin
from .pagination import AdminPageNumberPagination
from .serializers import PromotionAdminListSerializer, PromotionAdminSerializer


def _promotion_queryset():
    return Promotion.objects.select_related("listing", "event")


def _filter_promotions(qs, request):
    search = (request.query_params.get("search") or "").strip()
    if search:
        qs = qs.filter(
            Q(title__icontains=search)
            | Q(advertiser_name__icontains=search)
            | Q(subtitle__icontains=search)
        )

    placement = request.query_params.get("placement")
    if placement:
        qs = qs.filter(placement=placement)

    status_val = request.query_params.get("status")
    if status_val:
        qs = qs.filter(status=status_val)

    advertiser = (request.query_params.get("advertiser") or "").strip()
    if advertiser:
        qs = qs.filter(advertiser_name__icontains=advertiser)

    lifecycle = request.query_params.get("lifecycle")
    now = timezone.now()
    if lifecycle == "active_now":
        qs = qs.filter(is_active=True, status=Promotion.Status.ACTIVE)
    elif lifecycle == "scheduled":
        qs = qs.filter(status=Promotion.Status.SCHEDULED)
    elif lifecycle == "expired":
        qs = qs.filter(status=Promotion.Status.EXPIRED)
    elif lifecycle == "draft":
        qs = qs.filter(status=Promotion.Status.DRAFT)
    elif lifecycle == "paused":
        qs = qs.filter(status=Promotion.Status.PAUSED)

    event_id = request.query_params.get("event")
    if event_id:
        qs = qs.filter(event_id=event_id)

    listing_id = request.query_params.get("listing")
    if listing_id:
        qs = qs.filter(listing_id=listing_id)

    ordering = request.query_params.get("ordering") or "display_priority"
    allowed = {
        "display_priority",
        "-display_priority",
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
        qs = qs.order_by(ordering, "-created_at")
    else:
        qs = qs.order_by("display_priority", "-created_at")
    return qs


class AdminPromotionListCreateView(AdminAPIMixin, APIView):
    def get(self, request):
        qs = _filter_promotions(_promotion_queryset(), request)
        paginator = AdminPageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            PromotionAdminListSerializer(
                page, many=True, context={"request": request}
            ).data
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
    def get(self, request, promotion_id):
        promo = _promotion_queryset().filter(pk=promotion_id).first()
        if not promo:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(PromotionAdminSerializer(promo, context={"request": request}).data)

    def patch(self, request, promotion_id):
        promo = Promotion.objects.filter(pk=promotion_id).first()
        if not promo:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        before = PromotionAdminSerializer(promo, context={"request": request}).data
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
            before_state=before,
            after_state=PromotionAdminSerializer(promo, context={"request": request}).data,
        )
        return Response(PromotionAdminSerializer(promo, context={"request": request}).data)

    def delete(self, request, promotion_id):
        promo = Promotion.objects.filter(pk=promotion_id).first()
        if not promo:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        pid, title = promo.id, promo.title
        if promo.image:
            promo.image.delete(save=False)
        promo.delete()
        log_admin_action(
            actor=request.user,
            action_type="promotion.delete",
            object_type="promotion",
            object_id=pid,
            summary=f"Deleted promotion {title}",
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminPromotionReorderView(AdminAPIMixin, APIView):
    def post(self, request):
        order = request.data.get("order")
        if not isinstance(order, list) or not order:
            return Response(
                {"order": ["Provide a non-empty list of promotion IDs."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        normalized = []
        for item in order:
            try:
                promo_id = int(item)
            except (TypeError, ValueError):
                continue
            if promo_id not in normalized:
                normalized.append(promo_id)

        for index, promo_id in enumerate(normalized):
            Promotion.objects.filter(pk=promo_id).update(
                display_priority=index,
                updated_at=timezone.now(),
            )

        log_admin_action(
            actor=request.user,
            action_type="promotion.reorder",
            object_type="promotion",
            object_id=normalized[0] if normalized else 0,
            summary=f"Reordered {len(normalized)} promotions",
        )
        promos = _promotion_queryset().filter(pk__in=normalized).order_by(
            "display_priority", "-created_at"
        )
        return Response(
            PromotionAdminListSerializer(
                promos, many=True, context={"request": request}
            ).data
        )


class AdminPromotionActionView(AdminAPIMixin, APIView):
    def post(self, request, promotion_id, action):
        promo = Promotion.objects.filter(pk=promotion_id).first()
        if not promo:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if action == "activate":
            promo.is_active = True
            promo.save(update_fields=["is_active", "updated_at"])
            promo.refresh_status()
        elif action in {"pause", "deactivate"}:
            promo.is_active = False
            promo.status = Promotion.Status.PAUSED
            promo.save(update_fields=["is_active", "status", "updated_at"])
        elif action == "duplicate":
            duplicate = Promotion.objects.create(
                advertiser_name=promo.advertiser_name,
                listing=promo.listing,
                event=promo.event,
                placement=promo.placement,
                title=f"Copy of {promo.title}",
                subtitle=promo.subtitle,
                video_url=promo.video_url,
                cta_text=promo.cta_text,
                cta_link=promo.cta_link,
                target_route=promo.target_route,
                target_id=promo.target_id,
                channel=promo.channel,
                starts_at=promo.starts_at,
                ends_at=promo.ends_at,
                is_active=False,
                display_priority=promo.display_priority,
                sponsored_label=promo.sponsored_label,
                status=Promotion.Status.DRAFT,
                hero_approved=False,
                admin_note=promo.admin_note,
                billing_reference=promo.billing_reference,
                campaign_id=promo.campaign_id,
            )
            log_admin_action(
                actor=request.user,
                action_type="promotion.duplicate",
                object_type="promotion",
                object_id=duplicate.id,
                summary=f"Duplicated promotion {promo.title}",
            )
            return Response(
                PromotionAdminSerializer(duplicate, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )
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
