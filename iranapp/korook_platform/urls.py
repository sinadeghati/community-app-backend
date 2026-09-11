from django.urls import path

from .public_views import PublicEventListView, PublicPromotionListView, PublicHeroSlidesView
from .report_views import UserContentReportCreateView

urlpatterns = [
    path("events/", PublicEventListView.as_view(), name="public-events"),
    path("promotions/", PublicPromotionListView.as_view(), name="public-promotions"),
    path("hero-slides/", PublicHeroSlidesView.as_view(), name="public-hero-slides"),
    path("reports/", UserContentReportCreateView.as_view(), name="user-content-reports"),
]
