from unittest.mock import Mock, patch

from rest_framework.test import APITestCase


class TripAnalysisApiTests(APITestCase):
    def setUp(self):
        self.payload = {
            "origin": {"name": "Start", "latitude": 40, "longitude": -74},
            "destination": {"name": "Finish", "latitude": 41, "longitude": -73},
            "departure_datetime": "2026-11-20T08:00:00Z",
            "load_weight": 35000,
            "sampling_interval": 10,
        }
        self.route = {
            "route_id": "route-1",
            "geometry": [[-74, 40], [-73, 41]],
            "distance_meters": 5000,
            "duration_seconds": 3600,
        }

    @patch("apps.weather.services.checkpoint_weather.enrich_checkpoints_with_weather")
    @patch("apps.weather.services.open_meteo.OpenMeteoProvider")
    @patch("apps.routing.views.get_routing_provider")
    def test_trip_analysis_composes_routes_weather_risk_and_recommendation(self, routing_factory, weather_factory, enrich):
        routing = Mock()
        routing.get_routes.return_value = [self.route]
        routing_factory.return_value = routing
        weather_factory.return_value = Mock()

        def add_realistic_forecast(checkpoints, _provider):
            return [{
                **checkpoint,
                "wind_speed_mph": 18.0,
                "precipitation_inches_per_hour": 0.0,
                "snowfall_inches_per_hour": 0.0,
                "weather_timestamp": checkpoint["estimated_arrival_time"],
                "weather_match_delta_seconds": 0,
                "weather_data_status": "available",
                "weather_data_available": True,
            } for checkpoint in checkpoints]
        enrich.side_effect = add_realistic_forecast

        response = self.client.post("/api/trips/analyze/", self.payload, format="json")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["analysis_metadata"]["routing_provider"], "OpenRouteService")
        self.assertEqual(response.data["analysis_metadata"]["weather_provider"], "Open-Meteo")
        self.assertEqual(response.data["routes"][0]["route_id"], "route-1")
        self.assertEqual(len(response.data["routes"][0]["checkpoints"]), 2)
        self.assertEqual(response.data["routes"][0]["weather_coverage_percent"], 100)
        self.assertTrue(response.data["routes"][0]["safe_to_travel"])
        self.assertEqual(response.data["recommended_route_id"], "route-1")
        enrich.assert_called_once()

    def test_trip_analysis_rejects_bad_sampling_interval_and_identical_locations(self):
        bad_interval = {**self.payload, "sampling_interval": 15}
        identical_locations = {**self.payload, "destination": self.payload["origin"]}
        self.assertEqual(self.client.post("/api/trips/analyze/", bad_interval, format="json").status_code, 400)
        self.assertEqual(self.client.post("/api/trips/analyze/", identical_locations, format="json").status_code, 400)
