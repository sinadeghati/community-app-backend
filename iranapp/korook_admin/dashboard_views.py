from django.contrib.auth.models import User
from django.core.cache import cache
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from listings.models import Listing, ListingImage
from korook_platform.models import (
    BusinessClaim,
    ContentReport,
    Event,
    Promotion,
    UserPlatformProfile,
)

from .mixins import AdminAPIMixin

DASHBOARD_STATS_CACHE_KEY = "korook_admin:dashboard_stats"
DASHBOARD_STATS_CACHE_SECONDS = 60


def build_dashboard_stats():
    now = timezone.now()

    users_total = User.objects.count()

    profile_stats = UserPlatformProfile.objects.aggregate(
        users_suspended=Count(
            "id",
            filter=Q(account_status=UserPlatformProfile.AccountStatus.SUSPENDED),
        ),
        users_pending_review=Count(
            "id",
            filter=Q(account_status=UserPlatformProfile.AccountStatus.PENDING_REVIEW),
        ),
    )

    listing_stats = Listing.objects.aggregate(
        businesses_total=Count("id"),
        businesses_draft=Count("id", filter=Q(status=Listing.Status.DRAFT)),
        businesses_hidden=Count("id", filter=Q(status=Listing.Status.HIDDEN)),
        premium_active=Count(
            "id",
            filter=Q(premium_status=Listing.PremiumStatus.ACTIVE),
        ),
        featured_businesses=Count(
            "id",
            filter=Q(is_featured=True, status=Listing.Status.PUBLISHED),
        ),
    )

    event_stats = Event.objects.aggregate(
        events_total=Count("id"),
        events_draft=Count("id", filter=Q(status=Event.Status.DRAFT)),
        featured_events=Count(
            "id",
            filter=Q(is_featured=True, status=Event.Status.PUBLISHED),
        ),
    )

    report_stats = ContentReport.objects.aggregate(
        reports_new=Count("id", filter=Q(status=ContentReport.Status.NEW)),
        reports_in_review=Count(
            "id",
            filter=Q(status=ContentReport.Status.IN_REVIEW),
        ),
    )

    claims_pending = BusinessClaim.objects.filter(
        status=BusinessClaim.Status.PENDING
    ).count()

    media_pending = ListingImage.objects.filter(
        media_status=ListingImage.MediaStatus.PENDING_REVIEW
    ).count()

    promotions_active = Promotion.objects.filter(
        is_active=True,
        status=Promotion.Status.ACTIVE,
    ).filter(
        Q(starts_at__isnull=True) | Q(starts_at__lte=now),
        Q(ends_at__isnull=True) | Q(ends_at__gte=now),
    ).count()

    reports_new = report_stats["reports_new"]
    reports_in_review = report_stats["reports_in_review"]
    businesses_draft = listing_stats["businesses_draft"]
    events_draft = event_stats["events_draft"]

    return {
        "users_total": users_total,
        "users_suspended": profile_stats["users_suspended"],
        "users_pending_review": profile_stats["users_pending_review"],
        "businesses_total": listing_stats["businesses_total"],
        "businesses_draft": businesses_draft,
        "businesses_hidden": listing_stats["businesses_hidden"],
        "businesses_pending": businesses_draft,
        "events_total": event_stats["events_total"],
        "events_draft": events_draft,
        "events_pending": events_draft,
        "claims_pending": claims_pending,
        "reports_open": reports_new + reports_in_review,
        "reports_new": reports_new,
        "reports_in_review": reports_in_review,
        "media_pending_review": media_pending,
        "promotions_active": promotions_active,
        "premium_active": listing_stats["premium_active"],
        "featured_businesses": listing_stats["featured_businesses"],
        "featured_events": event_stats["featured_events"],
    }


class DashboardStatsView(AdminAPIMixin, APIView):
    """Dashboard KPIs for Korook admin command center."""

    def get(self, request):
        stats = cache.get(DASHBOARD_STATS_CACHE_KEY)
        if stats is None:
            stats = build_dashboard_stats()
            cache.set(DASHBOARD_STATS_CACHE_KEY, stats, DASHBOARD_STATS_CACHE_SECONDS)
        return Response(stats)
