"""Shared plain-text email delivery for account notifications."""

import json
import logging
import urllib.error
import urllib.request
from email.utils import parseaddr

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)

SENDGRID_API_URL = "https://api.sendgrid.com/v3/mail/send"


class SendGridEmailError(Exception):
    """Raised when SendGrid Web API fails to send email."""


def get_from_address():
    """
    Parse settings.DEFAULT_FROM_EMAIL into SendGrid-compatible name + email.

    Supports "Korook <noreply@korook.com>" and plain "noreply@korook.com".
    """
    raw_from = settings.DEFAULT_FROM_EMAIL.strip().strip('"').strip("'")
    name, email = parseaddr(raw_from)
    if not email:
        email = raw_from
    return {"name": name.strip(), "email": email.strip()}


def _send_via_sendgrid_web_api(*, to_email, subject, body, from_address, log_label):
    from_field = {"email": from_address["email"]}
    if from_address["name"]:
        from_field["name"] = from_address["name"]

    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": from_field,
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
            "SendGrid %s email failed for recipient=%s status=%s response=%s",
            log_label,
            to_email,
            exc.code,
            error_body,
        )
        raise SendGridEmailError(
            "Unable to send email. Please try again later."
        ) from exc
    except urllib.error.URLError as exc:
        logger.error(
            "SendGrid %s email connection error for recipient=%s: %s",
            log_label,
            to_email,
            exc.reason,
        )
        raise SendGridEmailError(
            "Unable to send email. Please try again later."
        ) from exc

    if not (200 <= status < 300):
        logger.error(
            "SendGrid %s email unexpected status for recipient=%s status=%s",
            log_label,
            to_email,
            status,
        )
        raise SendGridEmailError(
            "Unable to send email. Please try again later."
        )

    logger.info(
        "SendGrid %s email sent successfully to recipient=%s status=%s from_email=%s from_name=%r",
        log_label,
        to_email,
        status,
        from_address["email"],
        from_address["name"] or None,
    )


def send_plain_text_email(*, to_email, subject, body, log_label):
    """Send a plain-text email via SendGrid Web API or Django mail backend."""
    from_address = get_from_address()
    logger.info(
        "Sending %s email to recipient=%s from_email=%s from_name=%r",
        log_label,
        to_email,
        from_address["email"],
        from_address["name"] or None,
    )

    if getattr(settings, "USE_SENDGRID_WEB_API", False):
        _send_via_sendgrid_web_api(
            to_email=to_email,
            subject=subject,
            body=body,
            from_address=from_address,
            log_label=log_label,
        )
        return

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False,
        )
    except Exception:
        logger.exception(
            "Failed to send %s email for recipient=%s", log_label, to_email
        )
        raise
