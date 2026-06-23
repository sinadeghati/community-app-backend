from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from korook_admin.audit import log_admin_action
from listings.models import Listing, ListingImage

from .mixins import AdminAPIMixin
from .pagination import AdminPageNumberPagination
from .serializers import ListingAdminSerializer, ListingImageAdminSerializer


def _business_queryset():
    return Listing.objects.prefetch_related("images").order_by("-created_at")


def _filter_businesses(qs, request):
    search = (request.query_params.get("search") or "").strip()
    if search:
        qs = qs.filter(
            Q(title__icontains=search)
            | Q(business_name__icontains=search)
            | Q(city__icontains=search)
            | Q(category__icontains=search)
        )
    status_val = request.query_params.get("status")
    if status_val:
        qs = qs.filter(status=status_val)
    premium_status = request.query_params.get("premium_status")
    if premium_status:
        qs = qs.filter(premium_status=premium_status)
    return qs


class AdminBusinessListCreateView(AdminAPIMixin, APIView):
    def get(self, request):
        qs = _filter_businesses(_business_queryset(), request)
        paginator = AdminPageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            ListingAdminSerializer(page, many=True, context={"request": request}).data
        )

    def post(self, request):
        data = request.data.copy()
        owner_id = data.get("owner_id") or data.get("user_id")
        if not owner_id:
            return Response(
                {"detail": "owner_id or user_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = User.objects.filter(pk=owner_id).first()
        if not user:
            return Response({"detail": "User not found."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = ListingAdminSerializer(data=data, context={"request": request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        listing = serializer.save(user=user, owner=user)
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
            owner = User.objects.filter(pk=request.data["owner_id"]).first()
            if owner:
                listing.owner = owner
                listing.save(update_fields=["owner", "updated_at"])
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


class AdminBusinessImageView(AdminAPIMixin, APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, business_id):
        listing = Listing.objects.filter(pk=business_id).first()
        if not listing:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        role = request.data.get("role", ListingImage.Role.GALLERY)
        image = ListingImage.objects.create(
            listing=listing,
            image=request.data.get("image"),
            role=role,
            uploaded_by=request.user,
        )
        return Response(
            ListingImageAdminSerializer(image, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


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
