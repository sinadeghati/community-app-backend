"""Social login orchestration: verified provider identity → Korook user + JWT."""

from __future__ import annotations

import logging
import secrets
from typing import Optional, Tuple

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from rest_framework_simplejwt.tokens import RefreshToken

from korook_platform.models import UserPlatformProfile

from .models import ExternalIdentity, get_or_create_email_profile, is_user_email_verified
from .provider_verification import VerifiedProviderIdentity

logger = logging.getLogger(__name__)


class SocialAuthError(Exception):
    def __init__(self, message: str, code: str, status_code: int = 400):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


def _assert_platform_active(user: User) -> None:
    platform_profile = getattr(user, "platform_profile", None)
    if platform_profile and platform_profile.account_status in (
        UserPlatformProfile.AccountStatus.SUSPENDED,
        UserPlatformProfile.AccountStatus.DELETED,
    ):
        raise SocialAuthError("This account has been suspended.", "account_suspended", 403)


def issue_jwt_pair(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


def _unique_username(prefix: str, subject: str) -> str:
    base = f"{prefix}_{subject[:20]}".lower()
    base = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in base)
    if not User.objects.filter(username=base).exists():
        return base
    suffix = secrets.token_hex(3)
    return f"{base}_{suffix}"[:150]


def _apply_name(user: User, identity: VerifiedProviderIdentity) -> None:
    updates = []
    if identity.given_name and not user.first_name:
        user.first_name = identity.given_name[:150]
        updates.append("first_name")
    if identity.family_name and not user.last_name:
        user.last_name = identity.family_name[:150]
        updates.append("last_name")
    if updates:
        user.save(update_fields=updates)


def _mark_email_verified_if_applicable(user: User, identity: VerifiedProviderIdentity) -> None:
    profile = get_or_create_email_profile(user)
    if identity.email_verified or identity.provider == ExternalIdentity.Provider.APPLE:
        if not profile.email_verified:
            profile.mark_verified()


def _find_user_by_verified_email(email: str) -> Optional[User]:
    if not email:
        return None
    return User.objects.filter(email__iexact=email.strip()).first()


@transaction.atomic
def login_or_register_with_provider(
    identity: VerifiedProviderIdentity,
    *,
    apple_full_name: Optional[dict] = None,
) -> Tuple[User, bool, dict]:
    """
    Returns (user, created, jwt_payload).
    Rolls back user creation if identity row cannot be claimed.
    """
    if apple_full_name and not identity.given_name:
        identity = VerifiedProviderIdentity(
            provider=identity.provider,
            subject=identity.subject,
            email=identity.email,
            email_verified=identity.email_verified,
            given_name=(apple_full_name.get("givenName") or apple_full_name.get("given_name") or None),
            family_name=(apple_full_name.get("familyName") or apple_full_name.get("family_name") or None),
        )

    existing_identity = (
        ExternalIdentity.objects.select_for_update()
        .filter(provider=identity.provider, provider_subject=identity.subject)
        .select_related("user")
        .first()
    )
    if existing_identity:
        user = existing_identity.user
        _assert_platform_active(user)
        if identity.email and identity.email != existing_identity.provider_email:
            existing_identity.provider_email = identity.email
            existing_identity.save(update_fields=["provider_email", "updated_at"])
        return user, False, issue_jwt_pair(user)

    if identity.email:
        email_owner = _find_user_by_verified_email(identity.email)
        if email_owner and is_user_email_verified(email_owner):
            raise SocialAuthError(
                "An account with this email already exists. Sign in with your password, "
                "then link Google or Apple from your profile.",
                "existing_account_link_required",
                409,
            )

    prefix = "google" if identity.provider == ExternalIdentity.Provider.GOOGLE else "apple"
    username = _unique_username(prefix, identity.subject)
    email = (identity.email or "").strip()
    if not email:
        email = f"{username}@oauth.korook.invalid"

    user = User(username=username, email=email[:254])
    user.set_unusable_password()
    user.save()

    try:
        ExternalIdentity.objects.create(
            user=user,
            provider=identity.provider,
            provider_subject=identity.subject,
            provider_email=identity.email or "",
        )
    except IntegrityError:
        linked = (
            ExternalIdentity.objects.filter(
                provider=identity.provider,
                provider_subject=identity.subject,
            )
            .select_related("user")
            .first()
        )
        if linked:
            user.delete()
            _assert_platform_active(linked.user)
            return linked.user, False, issue_jwt_pair(linked.user)
        user.delete()
        raise

    _apply_name(user, identity)
    _mark_email_verified_if_applicable(user, identity)
    return user, True, issue_jwt_pair(user)


@transaction.atomic
def link_provider_to_user(user: User, identity: VerifiedProviderIdentity) -> ExternalIdentity:
    if identity.email:
        owner = _find_user_by_verified_email(identity.email)
        if owner and owner.pk != user.pk and is_user_email_verified(owner):
            raise SocialAuthError(
                "This provider email belongs to another Korook account.",
                "email_owned_by_other_account",
                409,
            )

    conflict = ExternalIdentity.objects.filter(
        provider=identity.provider,
        provider_subject=identity.subject,
    ).exclude(user=user).first()
    if conflict:
        raise SocialAuthError(
            "This provider account is already linked to another Korook user.",
            "provider_already_linked",
            409,
        )

    row = ExternalIdentity.objects.filter(
        user=user, provider=identity.provider
    ).first()
    if row:
        if row.provider_subject != identity.subject:
            raise SocialAuthError(
                "You already have a different account linked for this provider.",
                "provider_already_linked",
                409,
            )
        if identity.email and row.provider_email != identity.email:
            row.provider_email = identity.email
            row.save(update_fields=["provider_email", "updated_at"])
        _mark_email_verified_if_applicable(user, identity)
        return row

    ExternalIdentity.objects.create(
        user=user,
        provider=identity.provider,
        provider_subject=identity.subject,
        provider_email=identity.email or "",
    )
    row = ExternalIdentity.objects.get(user=user, provider=identity.provider)
    _mark_email_verified_if_applicable(user, identity)
    return row


def user_login_methods(user: User) -> dict:
    has_password = user.has_usable_password()
    providers = list(
        user.external_identities.values_list("provider", flat=True).distinct()
    )
    return {"has_password": has_password, "providers": providers}


def count_usable_login_methods(user: User) -> int:
    methods = user_login_methods(user)
    count = len(methods["providers"])
    if methods["has_password"]:
        count += 1
    return count


def disconnect_provider(user: User, provider: str) -> None:
    if provider not in (
        ExternalIdentity.Provider.GOOGLE,
        ExternalIdentity.Provider.APPLE,
    ):
        raise SocialAuthError("Unknown provider.", "invalid_provider", 400)

    if not ExternalIdentity.objects.filter(user=user, provider=provider).exists():
        raise SocialAuthError("Provider is not linked.", "not_linked", 404)

    if count_usable_login_methods(user) <= 1:
        raise SocialAuthError(
            "Add a password or another sign-in method before disconnecting this provider.",
            "cannot_disconnect_last_method",
            400,
        )

    ExternalIdentity.objects.filter(user=user, provider=provider).delete()
