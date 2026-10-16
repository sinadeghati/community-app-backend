from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class UserEmailProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="email_profile",
    )
    email_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    verification_code_hash = models.CharField(max_length=128, blank=True, null=True)
    verification_code_expires_at = models.DateTimeField(null=True, blank=True)
    verification_last_sent_at = models.DateTimeField(null=True, blank=True)
    verification_sends_in_window = models.PositiveSmallIntegerField(default=0)
    verification_window_started_at = models.DateTimeField(null=True, blank=True)
    avatar = models.ImageField(
        upload_to="profiles/avatars/",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "user email profile"
        verbose_name_plural = "user email profiles"

    def __str__(self):
        return f"{self.user.username} verified={self.email_verified}"

    def mark_verified(self):
        self.email_verified = True
        self.email_verified_at = timezone.now()
        self.save(update_fields=["email_verified", "email_verified_at"])


def get_or_create_email_profile(user):
    profile, _ = UserEmailProfile.objects.get_or_create(user=user)
    return profile


def is_user_email_verified(user):
    try:
        return user.email_profile.email_verified
    except UserEmailProfile.DoesNotExist:
        return False


class ExternalIdentity(models.Model):
    """OAuth provider subject linked to a Korook user (additive; backward compatible)."""

    class Provider(models.TextChoices):
        GOOGLE = "google", "Google"
        APPLE = "apple", "Apple"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="external_identities",
    )
    provider = models.CharField(max_length=16, choices=Provider.choices)
    provider_subject = models.CharField(max_length=255)
    provider_email = models.EmailField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_subject"],
                name="accounts_externalidentity_provider_subject_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "provider"]),
        ]

    def __str__(self):
        return f"{self.provider}:{self.provider_subject} → user {self.user_id}"
