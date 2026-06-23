from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

from .models import UserPlatformProfile


@receiver(post_save, sender=User)
def ensure_platform_profile(sender, instance, created, **kwargs):
    if created:
        UserPlatformProfile.objects.get_or_create(user=instance)
