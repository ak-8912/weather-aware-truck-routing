import os
from unittest.mock import Mock, patch

from django.core.cache import cache
from rest_framework.test import APITestCase


class RoutingApiTests(APITestCase):
    def setUp(self):
        cache.clear()

    @patch("apps.routing.views.get_routing_provider")
    def test_routes_endpoint_returns_only_routes_from_provider_and_notes_shortfall(self, provider_factory):
        provider = Mock()
        provider.get_routes.return_value = [{
            "route_id": "route-1",
            "geometry": [[-74.006, 40.7128], [-71.0589, 42.3601]],
            "distance_meters": 306000,
            "duration_seconds": 14400,
        }]
        provider_factory.return_value = provider

        response = self.client.post("/api/routes/", {
            "origin": {"name": "New York", "latitude": 40.7128, "longitude": -74.006},
            "destination": {"name": "Boston", "latitude": 42.3601, "longitude": -71.0589},
        }, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["route_count"], 1)
        self.assertEqual(len(response.data["routes"]), 1)
        self.assertIn("fewer than the requested maximum of 3", response.data["alternatives_notice"])
        self.assertEqual(response.data["provider"], "OpenRouteService")

    def test_route_request_rejects_identical_or_invalid_coordinates(self):
        same_location = self.client.post("/api/routes/", {
            "origin": {"latitude": 10, "longitude": 20},
            "destination": {"latitude": 10, "longitude": 20},
        }, format="json")
        invalid_location = self.client.post("/api/routes/", {
            "origin": {"latitude": 91, "longitude": 20},
            "destination": {"latitude": 10, "longitude": 21},
        }, format="json")

        self.assertEqual(same_location.status_code, 400)
        self.assertIn("error", same_location.data)
        self.assertEqual(invalid_location.status_code, 400)

    @patch.dict(os.environ, {"OPENROUTESERVICE_API_KEY": ""})
    def test_valid_route_request_without_provider_key_returns_configuration_error(self):
        response = self.client.post("/api/routes/", {
            "origin": {"latitude": 40.7128, "longitude": -74.006},
            "destination": {"latitude": 42.3601, "longitude": -71.0589},
        }, format="json")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["error"]["code"], "routing_provider_not_configured")

    @patch("apps.routing.views.get_routing_provider")
    def test_geocoding_endpoint_returns_suggestions_and_caches_provider_response(self, provider_factory):
        provider = Mock()
        provider.geocode.return_value = [{
            "name": "Boston, MA, United States", "latitude": 42.3601, "longitude": -71.0589,
            "address": {"locality": "Boston", "region": "Massachusetts", "country": "United States"},
        }]
        provider_factory.return_value = provider

        first = self.client.get("/api/geocoding/search/?q=Boston")
        second = self.client.get("/api/geocoding/search/?q=Boston")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.data["results"][0]["latitude"], 42.3601)
        self.assertEqual(second.data, first.data)
        provider.geocode.assert_called_once_with("Boston", 5)

    @patch("apps.routing.views.get_routing_provider")
    def test_geocoding_rejects_too_short_queries_without_calling_provider(self, provider_factory):
        response = self.client.get("/api/geocoding/search/?q=x")

        self.assertEqual(response.status_code, 400)
        provider_factory.assert_not_called()
