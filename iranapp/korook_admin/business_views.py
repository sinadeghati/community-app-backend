from django.contrib.auth.models import User
from django.db.models import OuterRef, Q, Subquery
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from geocode.nominatim import (
    GeocodeRateLimitError,
    GeocodeUpstreamError,
    forward_geocode_address_line,
)
from korook_admin.audit import log_admin_action
from listings.models import Listing, ListingImage
from listings.unclaimed import get_unclaimed_listing_user

from .business_admin import (
    apply_admin_create_defaults,
    invalid_zero_coordinates,
    resolve_coordinates_for_admin,
    validate_admin_business_required_fields,
    _client_ip,
)
from .mixins import AdminAPIMixin
from .pagination import AdminPageNumberPagination
from .serializers import (
    ListingAdminListSerializer,
    ListingAdminSerializer,
)


def _listing_image_subquery(role):
    return (
        ListingImage.objects.filter(
            listing_id=OuterRef("pk"),
            media_status=ListingImage.MediaStatus.ACTIVE,
            role=role,
        )
        .order_by("id")
        .values("image")[:1]
    )


def _business_list_queryset():
    return Listing.objects.annotate(
        thumbnail_logo=Subquery(_listing_image_subquery(ListingImage.Role.LOGO)),
        thumbnail_cover=Subquery(_listing_image_subquery(ListingImage.Role.COVER)),
    ).order_by("-created_at")


def _business_queryset():
    return Listing.objects.prefetch_related("images").order_by("-created_at")


def _filter_businesses(qs, request):
    search = (request.query_params.get("search") or "").strip()
    if search:
        qs = qs.filter(
            Q(title__icontains=search)
            | Q(business_name__icontains=search)
            | Q(city__icontains=search)
        )
    city = (request.query_params.get("city") or "").strip()
    if city:
        qs = qs.filter(city__icontains=city)
    status_val = request.query_params.get("status")
    if status_val:
        qs = qs.filter(status=status_val)
    premium_status = request.query_params.get("premium_status")
    if premium_status:
        qs = qs.filter(premium_status=premium_status)
    return qs


class AdminBusinessListCreateView(AdminAPIMixin, APIView):
    def get(self, request):
        qs = _filter_businesses(_business_list_queryset(), request)
        paginator = AdminPageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            ListingAdminListSerializer(
                page, many=True, context={"request": request}
            ).data
        )

    def post(self, request):
        data = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
        required_error = validate_admin_business_required_fields(data)
        if required_error:
            return required_error

        owner_id = data.get("owner_id") or data.get("user_id")
        owner_user = None
        if owner_id not in (None, ""):
            owner_user = User.objects.filter(pk=owner_id).first()
            if not owner_user:
                return Response({"detail": "User not found."}, status=status.HTTP_400_BAD_REQUEST)

        if "contact_info" not in data or data.get("contact_info") is None:
            data["contact_info"] = ""

        coord_error = resolve_coordinates_for_admin(data, request)
        if coord_error:
            return coord_error

        listing_user = owner_user or get_unclaimed_listing_user()
        serializer = ListingAdminSerializer(data=data, context={"request": request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        listing = serializer.save(user=listing_user, owner=owner_user)
        apply_admin_create_defaults(listing)
        log_admin_action(
            actor=request.user,
            action_type="business.create",
            object_type="listing",
            object_id=listing.id,
            summary=f"Created business {listing.title}",
        )
        return Response(
            ListingAdminSerializer(listing, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class AdminBusinessDetailView(AdminAPIMixin, APIView):
    def get(self, request, business_id):
        listing = _business_queryset().filter(pk=business_id).first()
        if not listing:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ListingAdminSerializer(listing, context={"request": request}).data)

    def patch(self, request, business_id):
        listing = Listing.objects.filter(pk=business_id).first()
        if not listing:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        before = ListingAdminSerializer(listing, context={"request": request}).data
        serializer = ListingAdminSerializer(
            listing, data=request.data, partial=True, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        listing = serializer.save()
        if "owner_id" in request.data:
            owner_raw = request.data.get("owner_id")
            if owner_raw in (None, ""):
                listing.owner = None
                listing.save(update_fields=["owner", "updated_at"])
            else:
                owner = User.objects.filter(pk=owner_raw).first()
                if not owner:
                    return Response(
                        {"detail": "User not found."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                listing.owner = owner
                listing.save(update_fields=["owner", "updated_at"])

        if invalid_zero_coordinates(listing.latitude, listing.longitude):
            return Response(
                {"detail": "Latitude and longitude cannot both be 0."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        log_admin_action(
            actor=request.user,
            action_type="business.update",
            object_type="listing",
            object_id=listing.id,
            summary=f"Updated business {listing.title}",
            before_state=before,
            after_state=ListingAdminSerializer(listing, context={"request": request}).data,
        )
        return Response(ListingAdminSerializer(listing, context={"request": request}).data)

    def delete(self, request, business_id):
        listing = Listing.objects.filter(pk=business_id).first()
        if not listing:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        title = listing.title
        lid = listing.id
        listing.delete()
        log_admin_action(
            actor=request.user,
            action_type="business.delete",
            object_type="listing",
            object_id=lid,
            summary=f"Deleted business {title}",
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminBusinessActionView(AdminAPIMixin, APIView):
    def post(self, request, business_id, action):
        listing = Listing.objects.filter(pk=business_id).first()
        if not listing:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if action == "publish":
            listing.status = Listing.Status.PUBLISHED
            listing.save(update_fields=["status", "updated_at"])
        elif action == "hide":
            listing.status = Listing.Status.HIDDEN
            listing.save(update_fields=["status", "updated_at"])
        elif action == "feature":
            listing.is_featured = bool(request.data.get("is_featured", True))
            listing.save(update_fields=["is_featured", "updated_at"])
        elif action == "sponsor":
            listing.is_sponsored = bool(request.data.get("is_sponsored", True))
            listing.save(update_fields=["is_sponsored", "updated_at"])
        elif action == "verify":
            listing.verified_badge = bool(request.data.get("verified_badge", True))
            if listing.verified_badge:
                listing.verified_at = timezone.now()
            else:
                listing.verified_at = None
            listing.save(update_fields=["verified_badge", "verified_at", "updated_at"])
        elif action == "assign-owner":
            owner = User.objects.filter(pk=request.data.get("user_id")).first()
            if not owner:
                return Response({"detail": "user_id required."}, status=status.HTTP_400_BAD_REQUEST)
            listing.owner = owner
            listing.save(update_fields=["owner", "updated_at"])
        else:
            return Response({"detail": "Unknown action."}, status=status.HTTP_400_BAD_REQUEST)
        log_admin_action(
            actor=request.user,
            action_type=f"business.{action}",
            object_type="listing",
            object_id=listing.id,
            summary=f"Business action {action} on {listing.title}",
        )
        return Response(ListingAdminSerializer(listing, context={"request": request}).data)


class AdminBusinessGeocodeView(AdminAPIMixin, APIView):
    """Resolve latitude/longitude for an admin-entered US address."""

    def post(self, request):
        address = (request.data.get("address") or "").strip()
        city = (request.data.get("city") or "").strip()
        state = (request.data.get("state") or "").strip()
        if not address or not city or not state:
            return Response(
                {"detail": "address, city, and state are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            coords = forward_geocode_address_line(
                address=address,
                city=city,
                state=state,
                client_ip=_client_ip(request),
            )
        except GeocodeRateLimitError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except GeocodeUpstreamError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        if not coords:
            return Response(
                {"detail": "Could not geocode this address. Check the street, city, and state."},
                status=status.HTTP_404_NOT_FOUND,
            )
        latitude, longitude = coords
        return Response({"latitude": latitude, "longitude": longitude})


class AdminPremiumListingsView(AdminAPIMixin, APIView):
    def get(self, request):
        qs = Listing.objects.exclude(
            premium_status=Listing.PremiumStatus.NONE
        ).order_by("display_priority", "-created_at")
        premium_status = request.query_params.get("premium_status")
        if premium_status:
            qs = qs.filter(premium_status=premium_status)
        paginator = AdminPageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            ListingAdminSerializer(page, many=True, context={"request": request}).data
        )
