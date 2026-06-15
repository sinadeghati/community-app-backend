"""
Password reset email helpers.

Reset links use Django's built-in PasswordResetTokenGenerator (default_token_generator).
The token is an HMAC derived from the user's pk, password hash, last_login timestamp,
and a timestamp embedded in the token — so it automatically invalidates when the
password changes or after the configured timeout (default: 3 days).

The uid in the link is the user's primary key, URL-safe base64-encoded — the same
encoding scheme Django's contrib.auth password reset views use. The frontend passes
uid + token back to a confirm endpoint to validate and set a new password.
"""

import json
import logging
import urllib.error
import urllib.request

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

logger = logging.getLogger(__name__)

SENDGRID_API_URL = "https://api.sendgrid.com/v3/mail/send"


class SendGridEmailError(Exception):
    """Raised when SendGrid Web API fails to send email."""


def build_password_reset_link(user):
    """
    Build a frontend reset URL: {FRONTEND_PASSWORD_RESET_URL}?uid=<b64-pk>&token=<token>

    uid  — urlsafe_base64_encode(force_bytes(user.pk))
    token — default_token_generator.make_token(user)
    """
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    base_url = settings.FRONTEND_PASSWORD_RESET_URL.rstrip("/")
    return f"{base_url}?uid={uid}&token={token}"


def _send_via_sendgrid_web_api(*, to_email, subject, body):
    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": settings.DEFAULT_FROM_EMAIL},
        "subject": subject,
        "content": [{"type": "text/plain", "value": body}],
    }
    request = urllib.request.Request(
        SENDGRID_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.SENDGRID_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status = response.status
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")[:500]
        logger.error(
            "SendGrid password reset email failed for recipient=%s status=%s response=%s",
            to_email,
            exc.code,
            error_body,
        )
        raise SendGridEmailError(
            "Unable to send password reset email. Please try again later."
        ) from exc
    except urllib.error.URLError as exc:
        logger.error(
            "SendGrid password reset email connection error for recipient=%s: %s",
            to_email,
            exc.reason,
        )
        raise SendGridEmailError(
            "Unable to send password reset email. Please try again later."
        ) from exc

    if not (200 <= status < 300):
        logger.error(
            "SendGrid password reset email unexpected status for recipient=%s status=%s",
            to_email,
            status,
        )
        raise SendGridEmailError(
            "Unable to send password reset email. Please try again later."
        )

    logger.info(
        "SendGrid password reset email sent successfully to recipient=%s status=%s",
        to_email,
        status,
    )


def send_password_reset_email(user):
    """Send a plain-text email with the password reset link."""
    reset_link = build_password_reset_link(user)
    subject = "Password reset instructions"
    message = (
        "Hello,\n\n"
        "You requested a password reset for your account.\n\n"
        f"Click the link below to reset your password:\n{reset_link}\n\n"
        "If you did not request this, you can safely ignore this email.\n"
    )

    if getattr(settings, "USE_SENDGRID_WEB_API", False):
        _send_via_sendgrid_web_api(
            to_email=user.email,
            subject=subject,
            body=message,
        )
        return

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception:
        logger.exception(
            "Failed to send password reset email for user pk=%s", user.pk
        )
