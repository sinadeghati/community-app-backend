from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from korook_admin.audit import log_admin_action
from korook_platform.models import Promotion

from .image_validation import validate_image_upload
from .mixins import AdminAPIMixin
from .serializers import PromotionAdminSerializer


def _get_promotion(promotion_id):
    return Promotion.objects.filter(pk=promotion_id).first()


class AdminPromotionHeroImageView(AdminAPIMixin, APIView):
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, promotion_id):
        promo = _get_promotion(promotion_id)
        if not promo:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            PromotionAdminSerializer(promo, context={"request": request}).data
        )

    def post(self, request, promotion_id):
        promo = _get_promotion(promotion_id)
        if not promo:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            uploaded = validate_image_upload(request.data.get("image"))
        except ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)
        if promo.image:
            promo.image.delete(save=False)
        promo.image = uploaded
        promo.save(update_fields=["image", "updated_at"])
        log_admin_action(
            actor=request.user,
            action_type="promotion.hero.upload",
            object_type="promotion",
            object_id=promo.id,
            summary=f"Uploaded hero image for {promo.title}",
        )
        return Response(
            PromotionAdminSerializer(promo, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def patch(self, request, promotion_id):
        promo = _get_promotion(promotion_id)
        if not promo:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if "image" not in request.data or not request.data.get("image"):
            return Response(
                {"image": ["Image file is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            uploaded = validate_image_upload(request.data.get("image"))
        except ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)
        if promo.image:
            promo.image.delete(save=False)
        promo.image = uploaded
        promo.save(update_fields=["image", "updated_at"])
        log_admin_action(
            actor=request.user,
            action_type="promotion.hero.replace",
            object_type="promotion",
            object_id=promo.id,
            summary=f"Replaced hero image for {promo.title}",
        )
        return Response(
            PromotionAdminSerializer(promo, context={"request": request}).data
        )

    def delete(self, request, promotion_id):
        promo = _get_promotion(promotion_id)
        if not promo:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if promo.image:
            promo.image.delete(save=False)
            promo.image = None
            promo.save(update_fields=["image", "updated_at"])
        log_admin_action(
            actor=request.user,
            action_type="promotion.hero.delete",
            object_type="promotion",
            object_id=promo.id,
            summary=f"Deleted hero image for {promo.title}",
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
