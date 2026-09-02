from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from geocode.nominatim import GeocodeRateLimitError, GeocodeUpstreamError


SAMPLE_RESULT = [
    {
        "place_id": 123456,
        "display_name": "4440 Twain Avenue, San Diego, CA 92115, USA",
        "lat": "32.7691",
        "lon": "-117.0734",
        "class": "building",
        "addresstype": "house",
        "address": {
            "house_number": "4440",
            "road": "Twain Avenue",
            "city": "San Diego",
            "state": "California",
            "postcode": "92115",
            "ISO3166-2-lvl4": "US-CA",
        },
    }
]


@override_settings(
    GEOCODE_RATE_LIMIT_PER_MINUTE=100,
    GEOCODE_UPSTREAM_MIN_INTERVAL_SECONDS=0,
)
class GeocodeSuggestViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        cache.clear()

    def test_missing_query_returns_400(self):
        response = self.client.get("/api/geocode/suggest/")
        self.assertEqual(response.status_code, 400)

    def test_short_query_returns_empty_list(self):
        response = self.client.get("/api/geocode/suggest/", {"q": "a"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    @patch("geocode.views.search_nominatim", return_value=SAMPLE_RESULT)
    def test_suggest_returns_upstream_results(self, mock_search):
        response = self.client.get(
            "/api/geocode/suggest/",
            {
                "q": "4440 Twain Ave, San Diego, CA",
                "format": "json",
                "addressdetails": "1",
                "limit": "12",
                "countrycodes": "us",
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["address"]["house_number"], "4440")
        mock_search.assert_called_once()

    @patch("geocode.views.search_nominatim", return_value=SAMPLE_RESULT)
    def test_structured_street_query_supported(self, mock_search):
        response = self.client.get(
            "/api/geocode/suggest/",
            {
                "street": "4440 Twain Ave",
                "city": "San Diego",
                "state": "CA",
                "countrycodes": "us",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        mock_search.assert_called_once()

    @patch(
        "geocode.views.search_nominatim",
        side_effect=GeocodeRateLimitError(
            "Too many geocoding requests. Please try again shortly."
        ),
    )
    def test_rate_limit_returns_429(self, _mock_search):
        response = self.client.get("/api/geocode/suggest/", {"q": "4440 Twain Ave"})
        self.assertEqual(response.status_code, 429)

    @patch(
        "geocode.views.search_nominatim",
        side_effect=GeocodeUpstreamError(
            "Geocoding service is temporarily busy. Please try again shortly.",
            status_code=429,
        ),
    )
    def test_upstream_429_returns_429(self, _mock_search):
        response = self.client.get("/api/geocode/suggest/", {"q": "4440 Twain Ave"})
        self.assertEqual(response.status_code, 429)

    @patch(
        "geocode.views.search_nominatim",
        side_effect=GeocodeUpstreamError(
            "Geocoding service is temporarily unavailable.",
            status_code=502,
        ),
    )
    def test_upstream_error_returns_502(self, _mock_search):
        response = self.client.get("/api/geocode/suggest/", {"q": "4440 Twain Ave"})
        self.assertEqual(response.status_code, 502)


class NominatimClientTests(TestCase):
    def setUp(self):
        cache.clear()

    @override_settings(GEOCODE_UPSTREAM_MIN_INTERVAL_SECONDS=0)
    @patch("geocode.nominatim.urllib.request.urlopen")
    def test_search_uses_cache_for_duplicate_queries(self, mock_urlopen):
        from geocode.nominatim import search_nominatim

        mock_response = mock_urlopen.return_value.__enter__.return_value
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'[{"place_id": 1}]'

        first = search_nominatim({"q": "4440 Twain Ave"})
        second = search_nominatim({"q": "4440 Twain Ave"})

        self.assertEqual(first, [{"place_id": 1}])
        self.assertEqual(second, [{"place_id": 1}])
        self.assertEqual(mock_urlopen.call_count, 1)

    def test_normalize_filters_unknown_params(self):
        from geocode.nominatim import normalize_query_params

        params = normalize_query_params(
            {
                "q": "4440 Twain Ave",
                "secret": "ignored",
                "limit": "6",
            }
        )
        self.assertEqual(params["q"], "4440 Twain Ave")
        self.assertEqual(params["limit"], "6")
        self.assertNotIn("secret", params)
