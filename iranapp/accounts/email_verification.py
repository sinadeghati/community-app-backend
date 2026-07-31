"""Email verification link and six-digit code delivery."""

from django.conf import settings

from .email_delivery import send_plain_text_email
from .models import get_or_create_email_profile
from .tokens import email_verification_token_generator
from .verification_codes import issue_verification_code
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


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
    """Send Korook verification email with a 6-digit code (and optional web link)."""
    profile = get_or_create_email_profile(user)
    code = issue_verification_code(profile)

    subject = "Your Korook verification code"
    message_lines = [
        "Hello,",
        "",
        "Thanks for signing up for Korook.",
        "",
        f"Your verification code is: {code}",
        "",
        "Enter this code in the Korook app to activate your account.",
        "This code expires in 30 minutes.",
    ]

    frontend_url = getattr(settings, "FRONTEND_EMAIL_VERIFICATION_URL", "").strip()
    if frontend_url:
        message_lines.extend(
            [
                "",
                "You can also verify using this link:",
                build_email_verification_link(user),
            ]
        )

    message_lines.extend(
        [
            "",
            "If you did not create this account, you can safely ignore this email.",
        ]
    )

    send_plain_text_email(
        to_email=user.email,
        subject=subject,
        body="\n".join(message_lines),
        log_label="email verification",
    )

    return code
