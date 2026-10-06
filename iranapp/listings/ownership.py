"""Listing ownership helpers shared by public and admin APIs."""

from django.db.models import Q

from .models import Listing


def listings_queryset_for_user(user):
    """Listings the user created or is assigned to own."""
    return Listing.objects.filter(Q(user=user) | Q(owner=user))


def user_can_manage_listing(user, listing):
    if not user or not user.is_authenticated:
        return False
    return listing.user_id == user.id or listing.owner_id == user.id
