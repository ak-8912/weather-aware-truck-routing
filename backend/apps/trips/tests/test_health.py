import os
from unittest.mock import patch

from rest_framework.test import APITestCase
from rest_framework.exceptions import ValidationError

from config.exceptions import api_exception_handler


class HealthEndpointTests(APITestCase):
    def test_health_reports_status_without_exposing_provider_secret(self):
        response = self.client.get("/api/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "ok")
        self.assertIn("routing_configured", response.data["providers"])
        self.assertEqual(response.data["providers"]["weather_provider"], "public")
        self.assertNotIn("OPENROUTESERVICE_API_KEY", str(response.data))

    def test_health_reflects_routing_key_presence_without_returning_it(self):
        with patch.dict(os.environ, {"OPENROUTESERVICE_API_KEY": "private-test-value"}):
            response = self.client.get("/api/health/")

        self.assertTrue(response.data["providers"]["routing_configured"])
        self.assertNotIn("private-test-value", str(response.data))

    def test_validation_errors_use_the_shared_api_error_envelope(self):
        response = api_exception_handler(ValidationError({"origin": ["This field is required."]}), {})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "invalid")
        self.assertIn("origin", response.data["error"]["details"])
