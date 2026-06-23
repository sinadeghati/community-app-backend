"""Six-digit email verification codes for the Korook mobile app."""

import secrets
from datetime import timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.utils import timezone

from .models import UserEmailProfile, get_or_create_email_profile

CODE_LENGTH = 6
CODE_TTL_MINUTES = 30
RESEND_COOLDOWN_SECONDS = 60
RESEND_MAX_PER_HOUR = 5


class VerificationRateLimitError(Exception):
    def __init__(self, message: str, retry_after_seconds: int | None = None):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


def _generate_code() -> str:
    return f"{secrets.randbelow(10 ** CODE_LENGTH):0{CODE_LENGTH}d}"


def _reset_window_if_needed(profile: UserEmailProfile, now):
    window_started = profile.verification_window_started_at
    if window_started is None or now - window_started >= timedelta(hours=1):
        profile.verification_window_started_at = now
        profile.verification_sends_in_window = 0


def issue_verification_code(profile: UserEmailProfile) -> str:
    """Create a fresh code, persist hash + expiry, enforce resend limits."""
    now = timezone.now()
    _reset_window_if_needed(profile, now)

    if profile.verification_last_sent_at is not None:
        elapsed = (now - profile.verification_last_sent_at).total_seconds()
        if elapsed < RESEND_COOLDOWN_SECONDS:
            retry_after = int(RESEND_COOLDOWN_SECONDS - elapsed)
            raise VerificationRateLimitError(
                f"Please wait {retry_after} seconds before requesting another code.",
                retry_after_seconds=retry_after,
            )

    if profile.verification_sends_in_window >= RESEND_MAX_PER_HOUR:
        raise VerificationRateLimitError(
            "Too many verification requests. Please try again in about an hour.",
            retry_after_seconds=3600,
        )

    code = _generate_code()
    profile.verification_code_hash = make_password(code)
    profile.verification_code_expires_at = now + timedelta(minutes=CODE_TTL_MINUTES)
    profile.verification_last_sent_at = now
    profile.verification_sends_in_window += 1
    profile.save(
        update_fields=[
            "verification_code_hash",
            "verification_code_expires_at",
            "verification_last_sent_at",
            "verification_sends_in_window",
            "verification_window_started_at",
        ]
    )
    return code


def verify_email_code(*, email: str, code: str) -> User:
    normalized_email = email.strip().lower()
    user = User.objects.filter(email__iexact=normalized_email).first()
    if user is None:
        raise ValueError("Invalid verification code.")

    profile = get_or_create_email_profile(user)
    if profile.email_verified:
        return user

    if not profile.verification_code_hash or not profile.verification_code_expires_at:
        raise ValueError("No active verification code. Request a new one.")

    if timezone.now() > profile.verification_code_expires_at:
        raise ValueError("This verification code has expired. Request a new one.")

    if not check_password(code.strip(), profile.verification_code_hash):
        raise ValueError("Invalid verification code.")

    profile.mark_verified()
    profile.verification_code_hash = None
    profile.verification_code_expires_at = None
    profile.save(
        update_fields=[
            "verification_code_hash",
            "verification_code_expires_at",
        ]
    )
    return user
