from decimal import Decimal, ROUND_HALF_UP

from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from accounts.models import UserBlock
from korook_platform.report_serializers import (
    ContentReportCreateResponseSerializer,
    ContentReportCreateSerializer,
)
from .content_filter import find_review_violation
from .models import BusinessReview, Listing
from .review_serializers import BusinessReviewSerializer


OWN_BUSINESS_MESSAGE = "You cannot review your own business."
DUPLICATE_REVIEW_MESSAGE = "You have already reviewed this business."
HELD_NOTICE = "This review is held for moderation and is not publicly visible."


def _published_listing(listing_id):
    return get_object_or_404(
        Listing,
        pk=listing_id,
        status=Listing.Status.PUBLISHED,
    )


def _approved_reviews(listing):
    return (
        BusinessReview.objects.filter(
            listing=listing,
            status=BusinessReview.Status.APPROVED,
        )
        .select_related("author")
        .order_by("-created_at", "-id")
    )


def _visible_approved_reviews(listing, user):
    reviews = _approved_reviews(listing)
    if getattr(user, "is_authenticated", False):
        blocked_ids = UserBlock.objects.filter(blocker=user).values("blocked_id")
        reviews = reviews.exclude(author_id__in=blocked_ids)
    return reviews


def _average_rating(reviews):
    count = reviews.count()
    if count == 0:
        return None, 0
    total = reviews.aggregate(total=Sum("rating"))["total"]
    average = (Decimal(total) / Decimal(count)).quantize(
        Decimal("0.1"),
        rounding=ROUND_HALF_UP,
    )
    return format(average, "f"), count


def _review_list_payload(listing, user):
    reviews = _visible_approved_reviews(listing, user)
    average_rating, review_count = _average_rating(reviews)
    visible = list(reviews)
    if getattr(user, "is_authenticated", False):
        visible_ids = {review.id for review in visible}
        own_reviews = (
            BusinessReview.objects.filter(listing=listing, author=user)
            .exclude(id__in=visible_ids)
            .select_related("author")
            .order_by("-created_at", "-id")
        )
        visible.extend(own_reviews)
    return {
        "listing_id": listing.id,
        "average_rating": average_rating,
        "review_count": review_count,
        "reviews": BusinessReviewSerializer(visible, many=True).data,
    }


def _review_is_blocked_for_viewer(user, review):
    if not getattr(user, "is_authenticated", False):
        return False
    if user.id == review.author_id:
        return False
    return UserBlock.objects.filter(blocker=user, blocked_id=review.author_id).exists()


def _status_for_text(review, text):
    if review is not None and review.status in (
        BusinessReview.Status.HIDDEN,
        BusinessReview.Status.REMOVED,
    ):
        return review.status
    if find_review_violation(text):
        return BusinessReview.Status.PENDING
    return BusinessReview.Status.APPROVED


def _review_payload(review):
    payload = BusinessReviewSerializer(review).data
    if review.status == BusinessReview.Status.PENDING:
        payload["moderation_notice"] = HELD_NOTICE
    return payload


def _user_owns_listing(user, listing):
    return user.id in {listing.user_id, listing.owner_id}


class ListingReviewListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [AllowAny()]

    def get(self, request, listing_id):
        listing = _published_listing(listing_id)
        return Response(_review_list_payload(listing, request.user))

    def post(self, request, listing_id):
        listing = _published_listing(listing_id)
        if _user_owns_listing(request.user, listing):
            return Response(
                {"detail": OWN_BUSINESS_MESSAGE},
                status=status.HTTP_403_FORBIDDEN,
            )
        if BusinessReview.objects.filter(listing=listing, author=request.user).exists():
            return Response(
                {"detail": DUPLICATE_REVIEW_MESSAGE},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = BusinessReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review_status = _status_for_text(None, serializer.validated_data["text"])
        try:
            with transaction.atomic():
                review = serializer.save(
                    listing=listing,
                    author=request.user,
                    status=review_status,
                )
        except IntegrityError:
            return Response(
                {"detail": DUPLICATE_REVIEW_MESSAGE},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(_review_payload(review), status=status.HTTP_201_CREATED)


class ListingReviewDetailView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated()]

    def _review(self, listing_id, review_id):
        listing = _published_listing(listing_id)
        return listing, get_object_or_404(
            BusinessReview.objects.select_related("author"),
            pk=review_id,
            listing=listing,
        )

    def _visible_to_reader(self, request, review):
        if review.status == BusinessReview.Status.APPROVED:
            return True
        user = request.user
        return user.is_authenticated and user.id == review.author_id

    def get(self, request, listing_id, review_id):
        _listing, review = self._review(listing_id, review_id)
        if _review_is_blocked_for_viewer(request.user, review):
            raise Http404
        if not self._visible_to_reader(request, review):
            raise Http404
        return Response(BusinessReviewSerializer(review).data)

    def patch(self, request, listing_id, review_id):
        _listing, review = self._review(listing_id, review_id)
        if _review_is_blocked_for_viewer(request.user, review):
            raise Http404
        if request.user.id != review.author_id:
            return Response(
                {"detail": "You can only edit your own review."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = BusinessReviewSerializer(review, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        next_text = serializer.validated_data.get("text", review.text)
        next_status = _status_for_text(review, next_text)
        review = serializer.save()
        if review.status != next_status:
            review.status = next_status
            review.save(update_fields=["status", "updated_at"])
        return Response(_review_payload(review))

    def delete(self, request, listing_id, review_id):
        _listing, review = self._review(listing_id, review_id)
        if _review_is_blocked_for_viewer(request.user, review):
            raise Http404
        if request.user.id != review.author_id:
            return Response(
                {"detail": "You can only delete your own review."},
                status=status.HTTP_403_FORBIDDEN,
            )
        review.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ListingReviewReportView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, listing_id, review_id):
        listing = _published_listing(listing_id)
        review = get_object_or_404(
            BusinessReview,
            pk=review_id,
            listing=listing,
            status=BusinessReview.Status.APPROVED,
        )
        if request.user.id == review.author_id:
            return Response(
                {"detail": "You cannot report your own review."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if _review_is_blocked_for_viewer(request.user, review):
            raise Http404

        details = request.data.get("details", request.data.get("description", ""))
        serializer = ContentReportCreateSerializer(
            data={
                "target_type": "review",
                "target_id": review.id,
                "reason": request.data.get("reason", ""),
                "description": details,
            },
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        report = serializer.save()
        return Response(
            ContentReportCreateResponseSerializer(report).data,
            status=status.HTTP_201_CREATED,
        )
