from django.contrib.auth.models import User
from django.db.models import Q
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


class DashboardStatsView(AdminAPIMixin, APIView):
    """Dashboard KPIs for Korook admin command center."""

    def get(self, request):
        now = timezone.now()
        users_total = User.objects.count()
        users_suspended = UserPlatformProfile.objects.filter(
            account_status=UserPlatformProfile.AccountStatus.SUSPENDED
        ).count()
        users_pending_review = UserPlatformProfile.objects.filter(
            account_status=UserPlatformProfile.AccountStatus.PENDING_REVIEW
        ).count()

        businesses_total = Listing.objects.count()
        businesses_draft = Listing.objects.filter(status=Listing.Status.DRAFT).count()
        businesses_hidden = Listing.objects.filter(status=Listing.Status.HIDDEN).count()

        events_total = Event.objects.count()
        events_draft = Event.objects.filter(status=Event.Status.DRAFT).count()

        claims_pending = BusinessClaim.objects.filter(
            status=BusinessClaim.Status.PENDING
        ).count()

        reports_new = ContentReport.objects.filter(
            status=ContentReport.Status.NEW
        ).count()
        reports_in_review = ContentReport.objects.filter(
            status=ContentReport.Status.IN_REVIEW
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

        premium_active = Listing.objects.filter(
            premium_status=Listing.PremiumStatus.ACTIVE
        ).count()

        featured_businesses = Listing.objects.filter(
            is_featured=True, status=Listing.Status.PUBLISHED
        ).count()
        featured_events = Event.objects.filter(
            is_featured=True, status=Event.Status.PUBLISHED
        ).count()

        return Response(
            {
                "users_total": users_total,
                "users_suspended": users_suspended,
                "users_pending_review": users_pending_review,
                "businesses_total": businesses_total,
                "businesses_draft": businesses_draft,
                "businesses_hidden": businesses_hidden,
                "businesses_pending": businesses_draft,
                "events_total": events_total,
                "events_draft": events_draft,
                "events_pending": events_draft,
                "claims_pending": claims_pending,
                "reports_open": reports_new + reports_in_review,
                "reports_new": reports_new,
                "reports_in_review": reports_in_review,
                "media_pending_review": media_pending,
                "promotions_active": promotions_active,
                "premium_active": premium_active,
                "featured_businesses": featured_businesses,
                "featured_events": featured_events,
            }
        )
