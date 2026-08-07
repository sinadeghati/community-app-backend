from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from korook_admin.audit import log_admin_action
from listings.models import Listing, ListingImage

from .gallery_order import read_gallery_order, sort_listing_images, write_gallery_order
from .image_validation import validate_image_upload
from .mixins import AdminAPIMixin
from .serializers import ListingImageAdminSerializer


def _get_listing(business_id):
    return Listing.objects.filter(pk=business_id).first()


def _get_image(business_id, image_id):
    return ListingImage.objects.filter(pk=image_id, listing_id=business_id).first()


def _demote_existing_role(listing, role, keep_image_id=None):
    qs = ListingImage.objects.filter(listing=listing, role=role)
    if keep_image_id:
        qs = qs.exclude(pk=keep_image_id)
    qs.update(role=ListingImage.Role.GALLERY)


def _set_exclusive_role(image, role):
    _demote_existing_role(image.listing, role, keep_image_id=image.id)
    image.role = role
    image.save(update_fields=["role"])
    return image


class AdminBusinessImageView(AdminAPIMixin, APIView):
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, business_id):
        listing = _get_listing(business_id)
        if not listing:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        images = sort_listing_images(
            listing.images.filter(media_status=ListingImage.MediaStatus.ACTIVE),
            listing,
        )
        return Response(
            ListingImageAdminSerializer(
                images, many=True, context={"request": request}
            ).data
        )

    def post(self, request, business_id):
        listing = _get_listing(business_id)
        if not listing:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            uploaded = validate_image_upload(request.data.get("image"))
        except ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

        role = request.data.get("role", ListingImage.Role.GALLERY)
        if role not in {
            ListingImage.Role.GALLERY,
            ListingImage.Role.COVER,
            ListingImage.Role.LOGO,
        }:
            return Response(
                {"role": ["Invalid role. Use cover, logo, or gallery."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        image = ListingImage.objects.create(
            listing=listing,
            image=uploaded,
            role=role,
            uploaded_by=request.user,
        )
        if role in {ListingImage.Role.COVER, ListingImage.Role.LOGO}:
            _set_exclusive_role(image, role)

        if role == ListingImage.Role.GALLERY:
            order = read_gallery_order(listing)
            order.append(image.id)
            write_gallery_order(listing, order)

        log_admin_action(
            actor=request.user,
            action_type="business.image.upload",
            object_type="listing",
            object_id=listing.id,
            summary=f"Uploaded {role} image for {listing.title}",
        )
        return Response(
            ListingImageAdminSerializer(image, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class AdminBusinessImageReorderView(AdminAPIMixin, APIView):
    def post(self, request, business_id):
        listing = _get_listing(business_id)
        if not listing:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        order = request.data.get("order")
        if not isinstance(order, list) or not order:
            return Response(
                {"order": ["Provide a non-empty list of image IDs."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        gallery_ids = set(
            ListingImage.objects.filter(
                listing=listing,
                role=ListingImage.Role.GALLERY,
                media_status=ListingImage.MediaStatus.ACTIVE,
            ).values_list("id", flat=True)
        )
        normalized = []
        for item in order:
            try:
                image_id = int(item)
            except (TypeError, ValueError):
                continue
            if image_id in gallery_ids and image_id not in normalized:
                normalized.append(image_id)

        for image_id in gallery_ids:
            if image_id not in normalized:
                normalized.append(image_id)

        write_gallery_order(listing, normalized)
        log_admin_action(
            actor=request.user,
            action_type="business.image.reorder",
            object_type="listing",
            object_id=listing.id,
            summary=f"Reordered gallery images for {listing.title}",
        )
        images = sort_listing_images(
            listing.images.filter(media_status=ListingImage.MediaStatus.ACTIVE),
            listing,
        )
        return Response(
            ListingImageAdminSerializer(
                images, many=True, context={"request": request}
            ).data
        )


class AdminBusinessImageDetailView(AdminAPIMixin, APIView):
    parser_classes = [MultiPartParser, FormParser]

    def patch(self, request, business_id, image_id):
        image = _get_image(business_id, image_id)
        if not image:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if "image" in request.data and request.data.get("image"):
            try:
                uploaded = validate_image_upload(request.data.get("image"))
            except Exception as exc:
                detail = getattr(exc, "detail", {"image": [str(exc)]})
                return Response(detail, status=status.HTTP_400_BAD_REQUEST)
            image.image.delete(save=False)
            image.image = uploaded
            image.uploaded_at = timezone.now()
            image.save(update_fields=["image", "uploaded_at"])

        if "role" in request.data:
            role = request.data.get("role")
            if role in {ListingImage.Role.COVER, ListingImage.Role.LOGO}:
                image = _set_exclusive_role(image, role)
            elif role == ListingImage.Role.GALLERY:
                image.role = role
                image.save(update_fields=["role"])

        log_admin_action(
            actor=request.user,
            action_type="business.image.replace",
            object_type="listing_image",
            object_id=image.id,
            summary=f"Updated image {image.id} for listing {image.listing_id}",
        )
        return Response(
            ListingImageAdminSerializer(image, context={"request": request}).data
        )

    def delete(self, request, business_id, image_id):
        image = _get_image(business_id, image_id)
        if not image:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        listing = image.listing
        image_id_value = image.id
        image.image.delete(save=False)
        image.delete()

        order = [item for item in read_gallery_order(listing) if item != image_id_value]
        write_gallery_order(listing, order)

        log_admin_action(
            actor=request.user,
            action_type="business.image.delete",
            object_type="listing",
            object_id=listing.id,
            summary=f"Deleted image {image_id_value} for {listing.title}",
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminBusinessImageActionView(AdminAPIMixin, APIView):
    def post(self, request, business_id, image_id, action):
        image = _get_image(business_id, image_id)
        if not image:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if action == "set-cover":
            image = _set_exclusive_role(image, ListingImage.Role.COVER)
        elif action == "set-logo":
            image = _set_exclusive_role(image, ListingImage.Role.LOGO)
        else:
            return Response({"detail": "Unknown action."}, status=status.HTTP_400_BAD_REQUEST)

        log_admin_action(
            actor=request.user,
            action_type=f"business.image.{action.replace('-', '_')}",
            object_type="listing_image",
            object_id=image.id,
            summary=f"{action} for listing {image.listing_id}",
        )
        return Response(
            ListingImageAdminSerializer(image, context={"request": request}).data
        )
