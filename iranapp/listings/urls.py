# iranapp/listings/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .business_claim_views import ListingBusinessClaimView
from .views import ListingViewSet, MyListingsViewSet

router = DefaultRouter()
router.register(r"listings", ListingViewSet, basename="listings")
router.register(r"my-listing", MyListingsViewSet, basename="my-listings")

urlpatterns = [
    path(
        "listings/<int:listing_id>/claim/",
        ListingBusinessClaimView.as_view(),
        name="listing-business-claim",
    ),
    path("", include(router.urls)),
]
print ("LISTINGS URLCONF LOADED")
print("ROUTER URLS:", [str(u) for u in router.urls])

