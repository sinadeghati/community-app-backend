"""Admin business create/update helpers."""

from rest_framework import status
from rest_framework.response import Response

from geocode.nominatim import (
    GeocodeRateLimitError,
    GeocodeUpstreamError,
    forward_geocode_address_line,
)
from listings.models import Listing


def _client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def invalid_zero_coordinates(latitude, longitude) -> bool:
    if latitude is None or longitude is None:
        return False
    try:
        return float(latitude) == 0.0 and float(longitude) == 0.0
    except (TypeError, ValueError):
        return False


def validate_admin_business_required_fields(data) -> Response | None:
    name = (data.get("business_name") or data.get("title") or "").strip()
    category = (data.get("category") or "").strip()
    address = (data.get("address") or "").strip()
    city = (data.get("city") or "").strip()
    state = (data.get("state") or "").strip()
    missing = []
    if not name:
        missing.append("business_name")
    if not category:
        missing.append("category")
    if not address:
        missing.append("address")
    if not city:
        missing.append("city")
    if not state:
        missing.append("state")
    if missing:
        return Response(
            {"detail": f"Required fields: {', '.join(missing)}."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not data.get("title"):
        data["title"] = name
    if not data.get("business_name"):
        data["business_name"] = name
    return None


def resolve_coordinates_for_admin(data, request) -> Response | None:
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    if latitude not in (None, "") and longitude not in (None, ""):
        if invalid_zero_coordinates(latitude, longitude):
            return Response(
                {"detail": "Latitude and longitude cannot both be 0."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return None

    try:
        coords = forward_geocode_address_line(
            address=(data.get("address") or "").strip(),
            city=(data.get("city") or "").strip(),
            state=(data.get("state") or "").strip(),
            client_ip=_client_ip(request),
        )
    except GeocodeRateLimitError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
    except GeocodeUpstreamError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

    if coords:
        data["latitude"], data["longitude"] = coords
    return None


def apply_admin_create_defaults(listing: Listing) -> Listing:
    listing.verified_badge = False
    listing.verified_at = None
    listing.is_featured = False
    listing.is_sponsored = False
    listing.premium_status = Listing.PremiumStatus.NONE
    listing.save(
        update_fields=[
            "verified_badge",
            "verified_at",
            "is_featured",
            "is_sponsored",
            "premium_status",
            "updated_at",
        ]
    )
    return listing
