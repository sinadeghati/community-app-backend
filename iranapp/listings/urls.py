# iranapp/listings/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .business_claim_views import ListingBusinessClaimView
from .review_views import (
    ListingReviewDetailView,
    ListingReviewListCreateView,
    ListingReviewReportView,
)
from .views import ListingViewSet, MyListingsViewSet

router = DefaultRouter()
router.register(r"listings", ListingViewSet, basename="listings")
router.register(r"my-listing", MyListingsViewSet, basename="my-listings")

urlpatterns = [
    path(
        "listings/<int:listing_id>/reviews/",
        ListingReviewListCreateView.as_view(),
        name="listing-reviews",
    ),
    path(
        "listings/<int:listing_id>/reviews/<int:review_id>/report/",
        ListingReviewReportView.as_view(),
        name="listing-review-report",
    ),
    path(
        "listings/<int:listing_id>/reviews/<int:review_id>/",
        ListingReviewDetailView.as_view(),
        name="listing-review-detail",
    ),
    path(
        "listings/<int:listing_id>/claim/",
        ListingBusinessClaimView.as_view(),
        name="listing-business-claim",
    ),
    path("", include(router.urls)),
]
print ("LISTINGS URLCONF LOADED")
print("ROUTER URLS:", [str(u) for u in router.urls])

