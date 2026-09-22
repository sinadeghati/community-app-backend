"""Placeholder auth user for listings created without an assigned owner."""

from django.contrib.auth.models import User

UNCLAIMED_LISTING_USERNAME = "korook_unclaimed_listings"


def get_unclaimed_listing_user() -> User:
    user, _ = User.objects.get_or_create(
        username=UNCLAIMED_LISTING_USERNAME,
        defaults={
            "email": "unclaimed-listings@korook.internal",
            "is_active": False,
        },
    )
    if user.has_usable_password():
        user.set_unusable_password()
        user.save(update_fields=["password"])
    return user


def listing_is_unclaimed(listing) -> bool:
    return listing.owner_id is None
