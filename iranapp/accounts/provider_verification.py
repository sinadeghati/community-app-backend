"""Verify Google / Apple identity tokens server-side. Never trust client-supplied subject or email."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Iterable, Optional

import jwt
from django.conf import settings
from jwt import PyJWKClient

logger = logging.getLogger(__name__)

APPLE_ISSUER = "https://appleid.apple.com"
APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"
GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}


class ProviderTokenError(Exception):
    """Raised when a provider token fails verification."""

    def __init__(self, message: str, code: str = "invalid_token"):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class VerifiedProviderIdentity:
    provider: str
    subject: str
    email: Optional[str]
    email_verified: bool
    given_name: Optional[str] = None
    family_name: Optional[str] = None


def _audiences_for(setting_name: str) -> list[str]:
    raw = getattr(settings, setting_name, "") or ""
    if isinstance(raw, (list, tuple)):
        return [str(v).strip() for v in raw if str(v).strip()]
    return [part.strip() for part in str(raw).split(",") if part.strip()]


def _google_audiences() -> list[str]:
    return _audiences_for("SOCIAL_AUTH_GOOGLE_CLIENT_IDS")


def _apple_audiences() -> list[str]:
    return _audiences_for("SOCIAL_AUTH_APPLE_CLIENT_IDS")


def verify_google_id_token(
    id_token: str,
    *,
    audiences: Optional[Iterable[str]] = None,
) -> VerifiedProviderIdentity:
    if not id_token or not str(id_token).strip():
        raise ProviderTokenError("Missing Google ID token.", code="missing_token")

    allowed = list(audiences) if audiences is not None else _google_audiences()
    if not allowed:
        raise ProviderTokenError(
            "Google client IDs are not configured on the server.",
            code="provider_not_configured",
        )

    try:
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as google_requests
    except ImportError:
        raise ProviderTokenError(
            "Google auth library is not installed.",
            code="provider_not_configured",
        )

    request = google_requests.Request()
    last_error: Optional[Exception] = None
    payload = None
    for audience in allowed:
        try:
            payload = google_id_token.verify_oauth2_token(
                id_token, request, audience=audience
            )
            break
        except ValueError as exc:
            last_error = exc
            payload = None

    if payload is None:
        message = str(last_error) if last_error else "Invalid Google ID token."
        code = "invalid_audience" if "audience" in message.lower() else "invalid_token"
        raise ProviderTokenError(message, code=code)

    issuer = payload.get("iss")
    if issuer not in GOOGLE_ISSUERS:
        raise ProviderTokenError("Invalid Google token issuer.", code="invalid_issuer")

    subject = str(payload.get("sub") or "").strip()
    if not subject:
        raise ProviderTokenError("Google token missing subject.", code="invalid_token")

    email = (payload.get("email") or "").strip() or None
    email_verified = bool(payload.get("email_verified"))

    from .models import ExternalIdentity

    return VerifiedProviderIdentity(
        provider=ExternalIdentity.Provider.GOOGLE,
        subject=subject,
        email=email,
        email_verified=email_verified,
        given_name=(payload.get("given_name") or None),
        family_name=(payload.get("family_name") or None),
    )


_apple_jwk_client: Optional[PyJWKClient] = None


def _apple_jwk() -> PyJWKClient:
    global _apple_jwk_client
    if _apple_jwk_client is None:
        _apple_jwk_client = PyJWKClient(APPLE_JWKS_URL)
    return _apple_jwk_client


def verify_apple_identity_token(
    identity_token: str,
    *,
    audiences: Optional[Iterable[str]] = None,
    nonce: Optional[str] = None,
) -> VerifiedProviderIdentity:
    if not identity_token or not str(identity_token).strip():
        raise ProviderTokenError("Missing Apple identity token.", code="missing_token")

    allowed = list(audiences) if audiences is not None else _apple_audiences()
    if not allowed:
        raise ProviderTokenError(
            "Apple client IDs are not configured on the server.",
            code="provider_not_configured",
        )

    try:
        signing_key = _apple_jwk().get_signing_key_from_jwt(identity_token)
        payload = jwt.decode(
            identity_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=allowed,
            issuer=APPLE_ISSUER,
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
    except jwt.ExpiredSignatureError:
        raise ProviderTokenError("Apple identity token has expired.", code="token_expired")
    except jwt.InvalidAudienceError:
        raise ProviderTokenError("Apple identity token audience is invalid.", code="invalid_audience")
    except jwt.PyJWTError as exc:
        raise ProviderTokenError(f"Invalid Apple identity token: {exc}", code="invalid_token")

    token_nonce = payload.get("nonce")
    if nonce:
        if not token_nonce:
            raise ProviderTokenError("Apple token missing nonce.", code="invalid_nonce")
        hashed = hashlib.sha256(str(nonce).encode("utf-8")).hexdigest()
        if str(token_nonce) not in (hashed, str(nonce)):
            raise ProviderTokenError("Apple nonce mismatch.", code="invalid_nonce")

    subject = str(payload.get("sub") or "").strip()
    if not subject:
        raise ProviderTokenError("Apple token missing subject.", code="invalid_token")

    email = (payload.get("email") or "").strip() or None
    email_verified_raw = payload.get("email_verified")
    if email_verified_raw is None:
        email_verified = bool(email)
    else:
        email_verified = str(email_verified_raw).lower() in ("true", "1", "yes")

    from .models import ExternalIdentity

    return VerifiedProviderIdentity(
        provider=ExternalIdentity.Provider.APPLE,
        subject=subject,
        email=email,
        email_verified=email_verified,
    )
