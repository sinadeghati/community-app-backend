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
