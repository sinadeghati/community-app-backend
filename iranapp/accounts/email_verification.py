"""Email verification link generation and delivery."""

from django.conf import settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .email_delivery import send_plain_text_email
from .tokens import email_verification_token_generator


def build_email_verification_link(user):
    """
    Build a frontend verification URL:
    {FRONTEND_EMAIL_VERIFICATION_URL}?uid=<b64-pk>&token=<token>
    """
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_verification_token_generator.make_token(user)
    base_url = settings.FRONTEND_EMAIL_VERIFICATION_URL.rstrip("/")
    return f"{base_url}?uid={uid}&token={token}"


def send_email_verification(user):
    """Send a plain-text email with the email verification link."""
    verification_link = build_email_verification_link(user)
    subject = "Verify your Korook email address"
    message = (
        "Hello,\n\n"
        "Thanks for signing up for Korook.\n\n"
        f"Click the link below to verify your email address:\n{verification_link}\n\n"
        "If you did not create this account, you can safely ignore this email.\n"
    )

    send_plain_text_email(
        to_email=user.email,
        subject=subject,
        body=message,
        log_label="email verification",
    )
