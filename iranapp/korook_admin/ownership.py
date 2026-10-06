"""Admin business ownership transfer — keeps user and owner in sync for mobile API."""

from django.contrib.auth.models import User

from listings.models import Listing


def display_name_for_user(user):
    if not user:
        return None
    full_name = f"{user.first_name} {user.last_name}".strip()
    return full_name or user.username


def transfer_listing_ownership(listing: Listing, new_owner: User) -> Listing:
    """
    Assign a business to a user for mobile management.

    Updates both listing.user and listing.owner so /api/my-listing/ and edit
    permissions work consistently. Does not change status, media, or other fields.
    """
    listing.user = new_owner
    listing.owner = new_owner
    listing.save(update_fields=["user", "owner", "updated_at"])
    return listing


def ownership_snapshot(listing: Listing) -> dict:
    owner = listing.owner or listing.user
    return {
        "business_id": listing.id,
        "business_name": listing.business_name or listing.title,
        "title": listing.title,
        "previous_owner_id": owner.id if owner else None,
        "previous_owner_username": owner.username if owner else None,
        "previous_owner_display_name": display_name_for_user(owner),
    }
