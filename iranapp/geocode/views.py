from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .nominatim import (
    GeocodeRateLimitError,
    GeocodeUpstreamError,
    search_nominatim,
)


def _client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


class GeocodeSuggestView(APIView):
    """Read-only address suggestion proxy for mobile clients."""

    permission_classes = [AllowAny]

    def get(self, request):
        q = (request.query_params.get("q") or "").strip()
        street = (request.query_params.get("street") or "").strip()
        if not q and not street:
            return Response(
                {"detail": "Query parameter q or street is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if q and len(q) < 2:
            return Response([], status=status.HTTP_200_OK)

        raw_params = {
            key: value
            for key, value in request.query_params.items()
            if value is not None
        }

        try:
            results = search_nominatim(raw_params, client_ip=_client_ip(request))
        except GeocodeRateLimitError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except GeocodeUpstreamError as exc:
            upstream_status = exc.status_code or status.HTTP_502_BAD_GATEWAY
            if upstream_status == 429:
                return Response({"detail": str(exc)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(results, status=status.HTTP_200_OK)
