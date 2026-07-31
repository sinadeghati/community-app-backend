from django.conf import settings
from django.db import models


class Listing(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        HIDDEN = "hidden", "Hidden"

    class PremiumStatus(models.TextChoices):
        NONE = "none", "None"
        TRIAL = "trial", "Trial"
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        PAUSED = "paused", "Paused"

    class SubscriptionStatus(models.TextChoices):
        NONE = "none", "None"
        TRIAL = "trial", "Trial"
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past due"
        CANCELED = "canceled", "Canceled"
        EXPIRED = "expired", "Expired"

    class PlanName(models.TextChoices):
        FREE = "free", "Free"
        PREMIUM = "premium", "Premium"
        SPONSORED = "sponsored", "Sponsored"

    class BillingCycle(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        YEARLY = "yearly", "Yearly"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="listings",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_listings",
    )

    title = models.CharField(max_length=255)
    business_name = models.CharField(max_length=255, blank=True, default="")
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    address = models.CharField(max_length=255, blank=True, default="")
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    about = models.TextField(null=True, blank=True)
    contact_info = models.CharField(max_length=255)
    phone = models.CharField(max_length=50, blank=True, default="")
    website = models.URLField(blank=True, default="")
    instagram = models.CharField(max_length=255, blank=True, default="")
    category = models.CharField(max_length=50, blank=True, default="")
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PUBLISHED,
        db_index=True,
    )
    is_featured = models.BooleanField(default=False, db_index=True)
    is_sponsored = models.BooleanField(default=False)
    premium_status = models.CharField(
        max_length=20,
        choices=PremiumStatus.choices,
        default=PremiumStatus.NONE,
        db_index=True,
    )
    premium_start_date = models.DateTimeField(null=True, blank=True)
    premium_end_date = models.DateTimeField(null=True, blank=True)
    subscription_status = models.CharField(
        max_length=20,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.NONE,
        db_index=True,
    )
    plan_name = models.CharField(
        max_length=20,
        choices=PlanName.choices,
        default=PlanName.FREE,
        db_index=True,
    )
    billing_cycle = models.CharField(
        max_length=20,
        choices=BillingCycle.choices,
        blank=True,
        default="",
    )
    subscription_start_date = models.DateTimeField(null=True, blank=True)
    subscription_end_date = models.DateTimeField(null=True, blank=True)
    subscription_canceled_at = models.DateTimeField(null=True, blank=True)
    stripe_customer_id = models.CharField(max_length=128, blank=True, default="")
    stripe_subscription_id = models.CharField(max_length=128, blank=True, default="")
    last_payment_status = models.CharField(max_length=64, blank=True, default="")
    monthly_price_cents = models.PositiveIntegerField(null=True, blank=True)
    billing_notes = models.TextField(blank=True, default="")
    logo_url = models.URLField(blank=True, default="")
    gallery_urls = models.TextField(blank=True, default="")
    display_priority = models.PositiveIntegerField(default=0, db_index=True)
    verified_badge = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    admin_note = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["city", "state"]),
        ]

    def save(self, *args, **kwargs):
        if not self.business_name:
            self.business_name = self.title
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.title} - {self.city}, {self.state}"

    @property
    def effective_owner(self):
        return self.owner or self.user


class ListingImage(models.Model):
    class Role(models.TextChoices):
        LOGO = "logo", "Logo"
        COVER = "cover", "Cover"
        GALLERY = "gallery", "Gallery"

    class MediaStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        HIDDEN = "hidden", "Hidden"
        PENDING_REVIEW = "pending_review", "Pending review"
        REJECTED = "rejected", "Rejected"

    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to="listings/")
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.GALLERY,
        db_index=True,
    )
    media_status = models.CharField(
        max_length=20,
        choices=MediaStatus.choices,
        default=MediaStatus.ACTIVE,
        db_index=True,
    )
    moderation_reason = models.CharField(max_length=255, blank=True, default="")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_listing_images",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="listing_image_reviews",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Image for Listing {self.listing_id} ({self.role})"
