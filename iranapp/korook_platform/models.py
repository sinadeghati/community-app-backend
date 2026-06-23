from django.conf import settings
from django.db import models
from django.utils import timezone


class UserPlatformProfile(models.Model):
    class Role(models.TextChoices):
        USER = "user", "User"
        BUSINESS_OWNER = "business_owner", "Business owner"
        ORGANIZER = "organizer", "Organizer"
        MODERATOR = "moderator", "Moderator"
        ADMIN = "admin", "Admin"

    class AccountStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        DELETED = "deleted", "Deleted"
        PENDING_REVIEW = "pending_review", "Pending review"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="platform_profile",
    )
    role = models.CharField(
        max_length=32,
        choices=Role.choices,
        default=Role.USER,
        db_index=True,
    )
    account_status = models.CharField(
        max_length=32,
        choices=AccountStatus.choices,
        default=AccountStatus.ACTIVE,
        db_index=True,
    )
    admin_note = models.TextField(blank=True, default="")
    suspended_at = models.DateTimeField(null=True, blank=True)
    suspended_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="suspensions_issued",
    )
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "user platform profile"
        verbose_name_plural = "user platform profiles"

    def __str__(self):
        return f"{self.user_id} ({self.role}, {self.account_status})"


class Event(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        HIDDEN = "hidden", "Hidden"

    class MediaStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        HIDDEN = "hidden", "Hidden"
        PENDING_REVIEW = "pending_review", "Pending review"
        REJECTED = "rejected", "Rejected"

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    category = models.CharField(max_length=100, blank=True, default="")
    starts_at = models.DateTimeField(db_index=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=255, blank=True, default="")
    address = models.CharField(max_length=255, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    state = models.CharField(max_length=100, blank=True, default="")
    zip_code = models.CharField(max_length=20, blank=True, default="")
    country = models.CharField(max_length=100, blank=True, default="")
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    organizer = models.CharField(max_length=255, blank=True, default="")
    ticket_url = models.URLField(blank=True, default="")
    ticket_provider_label = models.CharField(max_length=100, blank=True, default="")
    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_events",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    is_featured = models.BooleanField(default=False, db_index=True)
    is_sponsored = models.BooleanField(default=False)
    display_priority = models.PositiveIntegerField(default=0, db_index=True)
    cover_image = models.ImageField(upload_to="events/covers/", null=True, blank=True)
    cover_media_status = models.CharField(
        max_length=20,
        choices=MediaStatus.choices,
        default=MediaStatus.ACTIVE,
    )
    cover_moderation_reason = models.CharField(max_length=255, blank=True, default="")
    cover_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="event_cover_reviews",
    )
    cover_reviewed_at = models.DateTimeField(null=True, blank=True)
    admin_note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-starts_at"]

    def __str__(self):
        return self.title


class Promotion(models.Model):
    class Placement(models.TextChoices):
        HOME_HERO = "home_hero", "Home hero"
        EXPLORE_HERO = "explore_hero", "Explore hero"
        BUSINESS_FEATURED = "business_featured", "Business featured"
        EVENT_FEATURED = "event_featured", "Event featured"
        SPONSORED_CARD = "sponsored_card", "Sponsored card"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SCHEDULED = "scheduled", "Scheduled"
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        PAUSED = "paused", "Paused"

    advertiser_name = models.CharField(max_length=255)
    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="promotions",
    )
    event = models.ForeignKey(
        Event,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="promotions",
    )
    placement = models.CharField(
        max_length=32,
        choices=Placement.choices,
        db_index=True,
    )
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=500, blank=True, default="")
    image = models.ImageField(upload_to="promotions/", null=True, blank=True)
    video_url = models.URLField(blank=True, default="")
    cta_text = models.CharField(max_length=100, blank=True, default="")
    cta_link = models.URLField(blank=True, default="")
    target_route = models.CharField(max_length=255, blank=True, default="")
    target_id = models.CharField(max_length=64, blank=True, default="")
    channel = models.CharField(max_length=64, blank=True, default="")
    starts_at = models.DateTimeField(null=True, blank=True, db_index=True)
    ends_at = models.DateTimeField(null=True, blank=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    display_priority = models.PositiveIntegerField(default=0, db_index=True)
    sponsored_label = models.CharField(max_length=100, blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    hero_approved = models.BooleanField(default=False)
    admin_note = models.TextField(blank=True, default="")
    billing_reference = models.CharField(max_length=128, blank=True, default="")
    campaign_id = models.CharField(max_length=128, blank=True, default="")
    impression_cap = models.PositiveIntegerField(null=True, blank=True)
    budget_cents = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_priority", "-created_at"]

    def __str__(self):
        return f"{self.title} ({self.placement})"

    def refresh_status(self, save=True):
        now = timezone.now()
        if not self.is_active:
            new_status = self.Status.PAUSED
        elif self.starts_at and now < self.starts_at:
            new_status = self.Status.SCHEDULED
        elif self.ends_at and now > self.ends_at:
            new_status = self.Status.EXPIRED
        elif self.status == self.Status.DRAFT:
            new_status = self.Status.DRAFT
        else:
            new_status = self.Status.ACTIVE
        self.status = new_status
        if save:
            self.save(update_fields=["status", "updated_at"])
        return new_status


class BusinessClaim(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.CASCADE,
        related_name="claims",
    )
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="business_claims",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    admin_note = models.TextField(blank=True, default="")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="claims_reviewed",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Claim {self.id} listing={self.listing_id} ({self.status})"


class ContentReport(models.Model):
    class ObjectType(models.TextChoices):
        USER = "user", "User"
        LISTING = "listing", "Listing"
        EVENT = "event", "Event"
        LISTING_IMAGE = "listing_image", "Listing image"
        PROMOTION = "promotion", "Promotion"

    class Status(models.TextChoices):
        NEW = "new", "New"
        IN_REVIEW = "in_review", "In review"
        ACTIONED = "actioned", "Actioned"
        DISMISSED = "dismissed", "Dismissed"

    class ActionTaken(models.TextChoices):
        NONE = "none", "None"
        HIDE = "hide", "Hide"
        DELETE = "delete", "Delete"
        SUSPEND_USER = "suspend_user", "Suspend user"
        RESTORE = "restore", "Restore"

    reported_object_type = models.CharField(
        max_length=32,
        choices=ObjectType.choices,
        db_index=True,
    )
    reported_object_id = models.PositiveIntegerField(db_index=True)
    reported_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="reports_against",
    )
    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="content_reports",
    )
    event = models.ForeignKey(
        Event,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="content_reports",
    )
    listing_image = models.ForeignKey(
        "listings.ListingImage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="content_reports",
    )
    reason = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports_filed",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
        db_index=True,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports_reviewed",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    admin_note = models.TextField(blank=True, default="")
    action_taken = models.CharField(
        max_length=32,
        choices=ActionTaken.choices,
        default=ActionTaken.NONE,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Report {self.id} ({self.reported_object_type}:{self.reported_object_id})"


class AdminAuditLog(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="admin_audit_actions",
    )
    action_type = models.CharField(max_length=64, db_index=True)
    object_type = models.CharField(max_length=64, db_index=True)
    object_id = models.PositiveIntegerField(db_index=True)
    summary = models.CharField(max_length=500)
    before_state = models.JSONField(null=True, blank=True)
    after_state = models.JSONField(null=True, blank=True)
    admin_note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action_type} {self.object_type}:{self.object_id}"
