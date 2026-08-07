from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from korook_admin.audit import log_admin_action
from listings.models import Listing
from korook_platform.models import BusinessClaim

from .mixins import AdminAPIMixin
from .pagination import AdminPageNumberPagination
from .serializers import BusinessClaimAdminSerializer


class AdminClaimListView(AdminAPIMixin, APIView):
    """Paginated claim queue — default pending claims for dashboard workflow."""

    def get(self, request):
        qs = BusinessClaim.objects.select_related(
            "listing", "requester", "reviewed_by"
        ).order_by("-created_at")
        listing_id = request.query_params.get("listing")
        if listing_id:
            qs = qs.filter(listing_id=listing_id)
        status_filter = request.query_params.get("status")
        if status_filter == "all":
            pass
        elif status_filter:
            qs = qs.filter(status=status_filter)
        else:
            qs = qs.filter(status=BusinessClaim.Status.PENDING)
        paginator = AdminPageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = BusinessClaimAdminSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AdminClaimDetailView(AdminAPIMixin, APIView):
    def get(self, request, claim_id):
        claim = BusinessClaim.objects.select_related("listing", "requester").filter(
            pk=claim_id
        ).first()
        if not claim:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(BusinessClaimAdminSerializer(claim).data)


class AdminClaimApproveView(AdminAPIMixin, APIView):
    def post(self, request, claim_id):
        claim = BusinessClaim.objects.select_related("listing").filter(pk=claim_id).first()
        if not claim:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if claim.status != BusinessClaim.Status.PENDING:
            return Response(
                {"detail": "Claim is not pending."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        listing = claim.listing
        before = {"owner_id": listing.owner_id, "claim_status": claim.status}
        listing.owner = claim.requester
        listing.save(update_fields=["owner", "updated_at"])
        claim.status = BusinessClaim.Status.APPROVED
        claim.reviewed_by = request.user
        claim.reviewed_at = timezone.now()
        claim.admin_note = request.data.get("admin_note", claim.admin_note)
        claim.save()
        log_admin_action(
            actor=request.user,
            action_type="claim.approve",
            object_type="business_claim",
            object_id=claim.id,
            summary=f"Approved claim for listing {listing.id}",
            before_state=before,
            after_state={"owner_id": listing.owner_id, "claim_status": claim.status},
            admin_note=claim.admin_note,
        )
        return Response(BusinessClaimAdminSerializer(claim).data)


class AdminClaimRejectView(AdminAPIMixin, APIView):
    def post(self, request, claim_id):
        claim = BusinessClaim.objects.filter(pk=claim_id).first()
        if not claim:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if claim.status != BusinessClaim.Status.PENDING:
            return Response(
                {"detail": "Claim is not pending."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        before = {"claim_status": claim.status}
        claim.status = BusinessClaim.Status.REJECTED
        claim.reviewed_by = request.user
        claim.reviewed_at = timezone.now()
        claim.admin_note = request.data.get("admin_note", "")
        claim.save()
        log_admin_action(
            actor=request.user,
            action_type="claim.reject",
            object_type="business_claim",
            object_id=claim.id,
            summary=f"Rejected claim {claim.id}",
            before_state=before,
            after_state={"claim_status": claim.status},
            admin_note=claim.admin_note,
        )
        return Response(BusinessClaimAdminSerializer(claim).data)
