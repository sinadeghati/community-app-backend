import logging

from django.db import transaction

from listings.models import Listing

logger = logging.getLogger(__name__)


def revoke_refresh_token(raw_token: str | None) -> None:
    """Blacklist a refresh token when the optional blacklist app is available."""
    if not raw_token:
        return

    try:
        from rest_framework_simplejwt.tokens import RefreshToken

        RefreshToken(raw_token).blacklist()
    except Exception:
        logger.debug("Refresh token blacklist skipped or unavailable", exc_info=True)


def delete_user_account(user, *, refresh_token: str | None = None) -> None:
    """
    Permanently remove the user and related owned data.

    - Deletes owned listings (explicit delete before user removal).
    - Listing.user uses CASCADE as a database-level safety net.
    - UserEmailProfile is removed via CASCADE on user delete.
    - Attempts to blacklist the supplied refresh token when supported.
    """
    revoke_refresh_token(refresh_token)

    with transaction.atomic():
        Listing.objects.filter(user=user).delete()
        user.delete()
