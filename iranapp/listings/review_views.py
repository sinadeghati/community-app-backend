from decimal import Decimal, ROUND_HALF_UP

from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from .models import BusinessReview, Listing
from .review_serializers import BusinessReviewSerializer


OWN_BUSINESS_MESSAGE = "You cannot review your own business."
DUPLICATE_REVIEW_MESSAGE = "You have already reviewed this business."


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


def _review_list_payload(listing):
    reviews = _approved_reviews(listing)
    average_rating, review_count = _average_rating(reviews)
    return {
        "listing_id": listing.id,
        "average_rating": average_rating,
        "review_count": review_count,
        "reviews": BusinessReviewSerializer(reviews, many=True).data,
    }


def _user_owns_listing(user, listing):
    return user.id in {listing.user_id, listing.owner_id}


class ListingReviewListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [AllowAny()]

    def get(self, request, listing_id):
        listing = _published_listing(listing_id)
        return Response(_review_list_payload(listing))

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
        try:
            with transaction.atomic():
                review = serializer.save(
                    listing=listing,
                    author=request.user,
                    status=BusinessReview.Status.APPROVED,
                )
        except IntegrityError:
            return Response(
                {"detail": DUPLICATE_REVIEW_MESSAGE},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            BusinessReviewSerializer(review).data,
            status=status.HTTP_201_CREATED,
        )


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
        if not self._visible_to_reader(request, review):
            raise Http404
        return Response(BusinessReviewSerializer(review).data)

    def patch(self, request, listing_id, review_id):
        _listing, review = self._review(listing_id, review_id)
        if request.user.id != review.author_id:
            return Response(
                {"detail": "You can only edit your own review."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = BusinessReviewSerializer(review, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        review = serializer.save()
        return Response(BusinessReviewSerializer(review).data)

    def delete(self, request, listing_id, review_id):
        _listing, review = self._review(listing_id, review_id)
        if request.user.id != review.author_id:
            return Response(
                {"detail": "You can only delete your own review."},
                status=status.HTTP_403_FORBIDDEN,
            )
        review.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
