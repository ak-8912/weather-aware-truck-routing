import os
from unittest.mock import Mock, patch

import requests
from django.test import SimpleTestCase, override_settings

from apps.routing.services.openrouteservice import OpenRouteServiceProvider, normalize_geocoding_response
from apps.routing.services.routing_provider import (
    InvalidProviderResponse,
    ProviderAuthenticationError,
    ProviderConfigurationError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)


def route_response():
    return {"features": [{
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": [[-73.9, 40.7], [-73.8, 40.8]]},
        "properties": {"summary": {"distance": 1000, "duration": 100}},
    }]}


class OpenRouteServiceProviderTests(SimpleTestCase):
    @override_settings(OPENROUTESERVICE_BASE_URL="https://ors.example", OPENROUTESERVICE_TIMEOUT=9)
    @patch.dict(os.environ, {"OPENROUTESERVICE_API_KEY": "test-secret"})
    def test_directions_request_uses_hgv_and_requests_two_alternatives(self):
        response = Mock(status_code=200)
        response.json.return_value = route_response()
        session = Mock()
        session.request.return_value = response
        provider = OpenRouteServiceProvider(session=session)

        routes = provider.get_routes({"latitude": 40.7, "longitude": -73.9}, {"latitude": 40.8, "longitude": -73.8})

        self.assertEqual(len(routes), 1)
        args, kwargs = session.request.call_args
        self.assertEqual(args, ("POST", "https://ors.example/v2/directions/driving-hgv/geojson"))
        self.assertEqual(kwargs["json"]["coordinates"], [[-73.9, 40.7], [-73.8, 40.8]])
        self.assertEqual(kwargs["json"]["units"], "m")
        self.assertEqual(kwargs["json"]["alternative_routes"], {"target_count": 3, "share_factor": 0.6, "weight_factor": 1.4})
        self.assertEqual(kwargs["timeout"], 9)
        self.assertEqual(kwargs["headers"]["Authorization"], "test-secret")

    @override_settings(OPENROUTESERVICE_GEOCODING_BASE_URL="https://geo.example/pelias/v1")
    @patch.dict(os.environ, {"OPENROUTESERVICE_API_KEY": "test-secret"})
    def test_geocoding_uses_pelias_search_endpoint_and_query_text(self):
        response = Mock(status_code=200)
        response.json.return_value = {"features": []}
        session = Mock()
        session.request.return_value = response

        OpenRouteServiceProvider(session=session).geocode("New York", 4)

        args, kwargs = session.request.call_args
        self.assertEqual(args, ("GET", "https://geo.example/pelias/v1/search"))
        self.assertEqual(kwargs["params"], {"text": "New York", "size": 4})

    @override_settings(OPENROUTESERVICE_BASE_URL="https://ors.example")
    @patch.dict(os.environ, {"OPENROUTESERVICE_API_KEY": "test-secret"})
    def test_alternative_distance_limit_retries_for_primary_route_only(self):
        restricted = Mock(status_code=400)
        restricted.json.return_value = {"error": {"message": "Alternative route maximum distance exceeded"}}
        succeeded = Mock(status_code=200)
        succeeded.json.return_value = route_response()
        session = Mock()
        session.request.side_effect = [restricted, succeeded]

        routes = OpenRouteServiceProvider(session=session).get_routes(
            {"latitude": 40.7, "longitude": -73.9}, {"latitude": 40.8, "longitude": -73.8}
        )

        self.assertEqual(len(routes), 1)
        self.assertEqual(session.request.call_count, 2)
        first_payload = session.request.call_args_list[0].kwargs["json"]
        second_payload = session.request.call_args_list[1].kwargs["json"]
        self.assertIn("alternative_routes", first_payload)
        self.assertNotIn("alternative_routes", second_payload)

    @patch.dict(os.environ, {"OPENROUTESERVICE_API_KEY": ""})
    def test_missing_api_key_fails_without_request(self):
        session = Mock()
        provider = OpenRouteServiceProvider(session=session)

        with self.assertRaises(ProviderConfigurationError):
            provider.geocode("Boston")
        session.request.assert_not_called()

    @patch.dict(os.environ, {"OPENROUTESERVICE_API_KEY": "test-secret"})
    def test_timeout_is_translated_to_provider_timeout(self):
        session = Mock()
        session.request.side_effect = requests.Timeout()
        provider = OpenRouteServiceProvider(session=session)

        with self.assertRaises(ProviderTimeoutError):
            provider.geocode("Boston")

    @patch.dict(os.environ, {"OPENROUTESERVICE_API_KEY": "test-secret"})
    def test_rate_limit_and_auth_errors_are_translated(self):
        for status_code, expected_error in [(429, ProviderRateLimitError), (401, ProviderAuthenticationError)]:
            session = Mock()
            session.request.return_value = Mock(status_code=status_code)
            with self.assertRaises(expected_error):
                OpenRouteServiceProvider(session=session).geocode("Boston")

    @patch.dict(os.environ, {"OPENROUTESERVICE_API_KEY": "test-secret"})
    def test_invalid_json_is_not_treated_as_success(self):
        response = Mock(status_code=200)
        response.json.side_effect = ValueError("not json")
        session = Mock()
        session.request.return_value = response

        with self.assertRaises(InvalidProviderResponse):
            OpenRouteServiceProvider(session=session).geocode("Boston")

    def test_geocoding_normalizes_and_filters_invalid_features(self):
        results = normalize_geocoding_response({"features": [
            {"geometry": {"coordinates": [-71.0589, 42.3601]}, "properties": {"label": "Boston, MA", "locality": "Boston", "region": "Massachusetts", "country": "United States"}},
            {"geometry": {"coordinates": [181, 92]}, "properties": {"label": "Invalid"}},
        ]})

        self.assertEqual(results, [{
            "name": "Boston, MA", "latitude": 42.3601, "longitude": -71.0589,
            "address": {"locality": "Boston", "region": "Massachusetts", "country": "United States"},
        }])
