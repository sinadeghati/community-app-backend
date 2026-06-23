from django.urls import path

from .public_views import PublicEventListView, PublicPromotionListView, PublicHeroSlidesView

urlpatterns = [
    path("events/", PublicEventListView.as_view(), name="public-events"),
    path("promotions/", PublicPromotionListView.as_view(), name="public-promotions"),
    path("hero-slides/", PublicHeroSlidesView.as_view(), name="public-hero-slides"),
]
