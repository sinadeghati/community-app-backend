"""Server-side Nominatim client with caching, rate limiting, and polite usage."""

from __future__ import annotations

import hashlib
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

NOMINATIM_SEARCH_PATH = "/search"

ALLOWED_QUERY_PARAMS = frozenset(
    {
        "q",
        "street",
        "city",
        "state",
        "postalcode",
        "country",
        "countrycodes",
        "format",
        "addressdetails",
        "limit",
        "viewbox",
        "bounded",
    }
)

DEFAULT_FORMAT = "json"
DEFAULT_ADDRESSDETAILS = "1"
DEFAULT_LIMIT = "8"
DEFAULT_TIMEOUT_SECONDS = 8


class GeocodeRateLimitError(Exception):
    """Client exceeded Korook geocode proxy rate limit."""


class GeocodeUpstreamError(Exception):
    """Nominatim upstream failed or returned an unexpected response."""

    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _setting(name: str, default: str) -> str:
    return str(getattr(settings, name, default)).strip()


def get_user_agent() -> str:
    return _setting(
        "NOMINATIM_USER_AGENT",
        "KorookBackend/1.0 (https://korook.com; contact@korook.com)",
    )


def get_nominatim_base_url() -> str:
    return _setting(
        "NOMINATIM_BASE_URL",
        "https://nominatim.openstreetmap.org",
    ).rstrip("/")


def get_cache_seconds() -> int:
    return int(getattr(settings, "GEOCODE_CACHE_SECONDS", 3600))


def get_client_rate_limit_per_minute() -> int:
    return int(getattr(settings, "GEOCODE_RATE_LIMIT_PER_MINUTE", 30))


def get_upstream_min_interval_seconds() -> float:
    return float(getattr(settings, "GEOCODE_UPSTREAM_MIN_INTERVAL_SECONDS", 1.0))


def normalize_query_params(raw_params: dict[str, str]) -> dict[str, str]:
    cleaned: dict[str, str] = {}
    for key, value in raw_params.items():
        if key not in ALLOWED_QUERY_PARAMS:
            continue
        text = str(value).strip()
        if text:
            cleaned[key] = text

    cleaned.setdefault("format", DEFAULT_FORMAT)
    cleaned.setdefault("addressdetails", DEFAULT_ADDRESSDETAILS)
    if "limit" not in cleaned:
        cleaned["limit"] = DEFAULT_LIMIT

    return cleaned


def _cache_key(params: dict[str, str]) -> str:
    serialized = urllib.parse.urlencode(sorted(params.items()))
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return f"geocode:nominatim:{digest}"


def _client_rate_limit_key(client_ip: str) -> str:
    return f"geocode:rl:client:{client_ip}"


def _upstream_rate_limit_key() -> str:
    return "geocode:rl:upstream:last_request"


def enforce_client_rate_limit(client_ip: str) -> None:
    limit = get_client_rate_limit_per_minute()
    if limit <= 0:
        return

    key = _client_rate_limit_key(client_ip or "unknown")
    count = cache.get(key, 0)
    if count >= limit:
        raise GeocodeRateLimitError("Too many geocoding requests. Please try again shortly.")
    cache.set(key, count + 1, 60)


def _wait_for_upstream_slot() -> None:
    min_interval = get_upstream_min_interval_seconds()
    if min_interval <= 0:
        return

    key = _upstream_rate_limit_key()
    last_request = cache.get(key)
    if last_request is not None:
        elapsed = time.monotonic() - float(last_request)
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)

    cache.set(key, time.monotonic(), max(int(min_interval * 2), 2))


def search_nominatim(
    raw_params: dict[str, str],
    *,
    client_ip: str = "",
) -> list[dict]:
    params = normalize_query_params(raw_params)
    if not params.get("q") and not params.get("street"):
        return []

    enforce_client_rate_limit(client_ip)

    cache_key = _cache_key(params)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    query = urllib.parse.urlencode(params)
    url = f"{get_nominatim_base_url()}{NOMINATIM_SEARCH_PATH}?{query}"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": get_user_agent(),
        },
        method="GET",
    )

    _wait_for_upstream_slot()

    try:
        with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
            body = response.read().decode("utf-8")
            status_code = response.getcode()
    except urllib.error.HTTPError as exc:
        status_code = exc.code
        body = exc.read().decode("utf-8", errors="replace")
        logger.warning(
            "Nominatim HTTP error status=%s body=%s",
            status_code,
            body[:300],
        )
        if status_code == 429:
            raise GeocodeUpstreamError(
                "Geocoding service is temporarily busy. Please try again shortly.",
                status_code=429,
            ) from exc
        raise GeocodeUpstreamError(
            "Geocoding service is temporarily unavailable.",
            status_code=status_code,
        ) from exc
    except urllib.error.URLError as exc:
        logger.warning("Nominatim network error: %s", exc)
        raise GeocodeUpstreamError(
            "Geocoding service is temporarily unavailable."
        ) from exc
    except TimeoutError as exc:
        logger.warning("Nominatim timeout")
        raise GeocodeUpstreamError(
            "Geocoding service timed out. Please try again."
        ) from exc

    if status_code != 200:
        raise GeocodeUpstreamError(
            "Geocoding service is temporarily unavailable.",
            status_code=status_code,
        )

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        logger.warning("Nominatim invalid JSON: %s", body[:300])
        raise GeocodeUpstreamError("Geocoding service returned an invalid response.") from exc

    if not isinstance(payload, list):
        raise GeocodeUpstreamError("Geocoding service returned an invalid response.")

    cache.set(cache_key, payload, get_cache_seconds())
    return payload
