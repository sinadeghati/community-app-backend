from django.urls import path

from .event_api_views import (
    PublicEventListCreateView,
    UserEventDetailView,
    UserEventMineListView,
)
from .public_views import PublicPromotionListView, PublicHeroSlidesView
from .report_views import UserContentReportCreateView

urlpatterns = [
    path("events/mine/", UserEventMineListView.as_view(), name="user-events-mine"),
    path("events/<int:event_id>/", UserEventDetailView.as_view(), name="user-event-detail"),
    path("events/", PublicEventListCreateView.as_view(), name="public-events"),
    path("promotions/", PublicPromotionListView.as_view(), name="public-promotions"),
    path("hero-slides/", PublicHeroSlidesView.as_view(), name="public-hero-slides"),
    path("reports/", UserContentReportCreateView.as_view(), name="user-content-reports"),
]
