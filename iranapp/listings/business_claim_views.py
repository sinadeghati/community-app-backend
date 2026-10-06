"""Authenticated business ownership claim requests for published unclaimed listings."""

from django.db import IntegrityError, transaction
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from korook_platform.models import BusinessClaim
from listings.unclaimed import listing_is_unclaimed

from .models import Listing


class BusinessClaimSubmitSerializer(serializers.Serializer):
    claimant_name = serializers.CharField(max_length=255)
    relationship_role = serializers.CharField(max_length=128)
    contact_email = serializers.EmailField()
    contact_phone = serializers.CharField(max_length=50)
    verification_message = serializers.CharField(min_length=10, max_length=5000)


def _published_listing_or_404(listing_id):
    return (
        Listing.objects.filter(pk=listing_id, status=Listing.Status.PUBLISHED)
        .first()
    )


class ListingBusinessClaimView(APIView):
    """GET claim eligibility/status; POST a new claim request."""

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return []

    def get(self, request, listing_id):
        listing = _published_listing_or_404(listing_id)
        if not listing:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        payload = {
            "listing_id": listing.id,
            "is_unclaimed": listing_is_unclaimed(listing),
            "user_claim_status": None,
        }
        user = request.user
        if user and user.is_authenticated:
            claim = (
                BusinessClaim.objects.filter(listing=listing, requester=user)
                .order_by("-created_at")
                .first()
            )
            if claim:
                payload["user_claim_status"] = claim.status
        return Response(payload)

    def post(self, request, listing_id):
        listing = _published_listing_or_404(listing_id)
        if not listing:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if not listing_is_unclaimed(listing):
            return Response(
                {"detail": "This business already has an owner."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if BusinessClaim.objects.filter(
            listing=listing,
            requester=request.user,
            status=BusinessClaim.Status.PENDING,
        ).exists():
            return Response(
                {"detail": "You already have a pending claim for this business."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = BusinessClaimSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            with transaction.atomic():
                claim = BusinessClaim.objects.create(
                    listing=listing,
                    requester=request.user,
                    status=BusinessClaim.Status.PENDING,
                    claimant_name=data["claimant_name"].strip(),
                    relationship_role=data["relationship_role"].strip(),
                    contact_email=data["contact_email"].strip(),
                    contact_phone=data["contact_phone"].strip(),
                    verification_message=data["verification_message"].strip(),
                )
        except IntegrityError:
            return Response(
                {"detail": "You already have a pending claim for this business."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "id": claim.id,
                "status": claim.status,
                "message": "Your claim request has been submitted for review.",
            },
            status=status.HTTP_201_CREATED,
        )
