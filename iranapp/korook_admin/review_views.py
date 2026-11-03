from django.db.models import Count
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from korook_admin.audit import log_admin_action
from korook_platform.models import ContentReport
from listings.models import BusinessReview
from listings.review_moderation import REVIEW_MODERATION_STATUSES, moderate_review

from .mixins import AdminAPIMixin
from .pagination import AdminPageNumberPagination
from .serializers import AdminBusinessReviewSerializer


REPORT_ACTION_TAKEN = {
    "hide": ContentReport.ActionTaken.HIDE,
    "remove": ContentReport.ActionTaken.DELETE,
    "restore": ContentReport.ActionTaken.RESTORE,
    "approve": ContentReport.ActionTaken.RESTORE,
}


def _review_queryset():
    return (
        BusinessReview.objects.select_related("author", "listing")
        .annotate(report_count=Count("content_reports"))
        .order_by("-created_at", "-id")
    )


class AdminReviewListView(AdminAPIMixin, APIView):
    def get(self, request):
        reviews = _review_queryset()
        status_value = (request.query_params.get("status") or "").strip()
        if status_value == "reported":
            reviews = reviews.filter(report_count__gt=0)
        elif status_value:
            reviews = reviews.filter(status=status_value)
        listing_id = request.query_params.get("listing_id")
        if listing_id:
            reviews = reviews.filter(listing_id=listing_id)
        paginator = AdminPageNumberPagination()
        page = paginator.paginate_queryset(reviews, request)
        return paginator.get_paginated_response(
            AdminBusinessReviewSerializer(page, many=True).data
        )


class AdminReviewDetailView(AdminAPIMixin, APIView):
    def get(self, request, review_id):
        review = _review_queryset().filter(pk=review_id).first()
        if review is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(AdminBusinessReviewSerializer(review).data)


class AdminReviewActionView(AdminAPIMixin, APIView):
    def post(self, request, review_id, action):
        if action not in REVIEW_MODERATION_STATUSES:
            return Response({"detail": "Unknown action."}, status=status.HTTP_400_BAD_REQUEST)
        review = _review_queryset().filter(pk=review_id).first()
        if review is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        before_status = review.status
        moderate_review(review, action)
        now = timezone.now()
        ContentReport.objects.filter(
            reported_object_type=ContentReport.ObjectType.REVIEW,
            reported_object_id=review.id,
            status__in=[ContentReport.Status.NEW, ContentReport.Status.IN_REVIEW],
        ).update(
            status=ContentReport.Status.ACTIONED,
            action_taken=REPORT_ACTION_TAKEN[action],
            reviewed_by=request.user,
            reviewed_at=now,
        )
        log_admin_action(
            actor=request.user,
            action_type=f"review.{action}",
            object_type="business_review",
            object_id=review.id,
            summary=f"Review {action} changed status from {before_status} to {review.status}",
            before_state={"status": before_status},
            after_state={"status": review.status},
            admin_note=request.data.get("admin_note", ""),
        )
        return Response(AdminBusinessReviewSerializer(review).data)
