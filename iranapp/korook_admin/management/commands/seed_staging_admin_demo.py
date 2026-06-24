from datetime import timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone

from accounts.models import get_or_create_email_profile
from korook_platform.models import (
    BusinessClaim,
    ContentReport,
    Event,
    Promotion,
    UserPlatformProfile,
)
from listings.models import Listing


class Command(BaseCommand):
    help = "Seed staging demo data for Korook admin screenshots."

    def handle(self, *args, **options):
        staff, created = User.objects.get_or_create(
            username="korook_admin_demo",
            defaults={
                "email": "admin-demo@korook.com",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created:
            staff.set_password("KorookAdminDemo!2026")
            staff.save()
        else:
            staff.is_staff = True
            staff.is_superuser = True
            staff.set_password("KorookAdminDemo!2026")
            staff.save()
        get_or_create_email_profile(staff).mark_verified()
        UserPlatformProfile.objects.filter(user=staff).update(
            role=UserPlatformProfile.Role.ADMIN,
            account_status=UserPlatformProfile.AccountStatus.ACTIVE,
        )

        owner, _ = User.objects.get_or_create(
            username="demo_owner",
            defaults={"email": "owner-demo@korook.com"},
        )
        if not owner.has_usable_password():
            owner.set_password("DemoOwner!2026")
            owner.save()
        get_or_create_email_profile(owner).mark_verified()

        listing, _ = Listing.objects.get_or_create(
            user=owner,
            title="Demo Persian Cafe",
            defaults={
                "business_name": "Demo Persian Cafe",
                "city": "Los Angeles",
                "state": "CA",
                "contact_info": "owner-demo@korook.com",
                "category": "Restaurant",
                "status": Listing.Status.PUBLISHED,
                "is_featured": True,
            },
        )

        event, _ = Event.objects.get_or_create(
            title="Nowruz Community Festival",
            owner=owner,
            defaults={
                "description": "Staging demo event",
                "category": "Festival",
                "starts_at": timezone.now() + timedelta(days=14),
                "city": "Los Angeles",
                "state": "CA",
                "status": Event.Status.PUBLISHED,
                "is_featured": True,
            },
        )

        Promotion.objects.get_or_create(
            title="Welcome to Korook Staging",
            placement=Promotion.Placement.HOME_HERO,
            defaults={
                "advertiser_name": "Korook",
                "subtitle": "Discover Persian-owned businesses",
                "cta_text": "Explore",
                "cta_link": "https://korook.com",
                "status": Promotion.Status.ACTIVE,
                "is_active": True,
                "hero_approved": True,
                "display_priority": 1,
            },
        )

        claim, _ = BusinessClaim.objects.get_or_create(
            listing=listing,
            requester=owner,
            defaults={"status": BusinessClaim.Status.PENDING},
        )
        if claim.status != BusinessClaim.Status.PENDING:
            claim.status = BusinessClaim.Status.PENDING
            claim.reviewed_by = None
            claim.reviewed_at = None
            claim.save()

        ContentReport.objects.update_or_create(
            reported_object_type=ContentReport.ObjectType.LISTING,
            reported_object_id=listing.id,
            defaults={
                "listing": listing,
                "reason": "spam",
                "description": "Staging demo report",
                "status": ContentReport.Status.NEW,
                "action_taken": ContentReport.ActionTaken.NONE,
            },
        )

        self.stdout.write(self.style.SUCCESS("Demo admin: korook_admin_demo / KorookAdminDemo!2026"))
        self.stdout.write(self.style.SUCCESS(f"Seeded listing={listing.id} event={event.id} claim={claim.id}"))
