from datetime import datetime, timedelta, timezone
from unittest import TestCase
from unittest.mock import Mock

from apps.weather.services.checkpoint_weather import (
    CheckpointWeatherError,
    enrich_checkpoints_with_weather,
)
from apps.weather.services.weather_provider import InvalidWeatherResponse


def checkpoint(eta, latitude=42.36, longitude=-71.05, checkpoint_id="cp-1"):
    return {
        "checkpoint_id": checkpoint_id,
        "latitude": latitude,
        "longitude": longitude,
        "estimated_arrival_time": eta,
    }


def weather_row(timestamp, wind=12, precipitation=0.1, snowfall=0):
    return {
        "timestamp": timestamp,
        "wind_speed_mph": wind,
        "precipitation_inches_per_hour": precipitation,
        "snowfall_inches_per_hour": snowfall,
    }


class CheckpointWeatherTests(TestCase):
    def test_matches_checkpoint_to_nearest_hour_and_marks_complete_coverage(self):
        eta = datetime(2026, 11, 20, 8, 20, tzinfo=timezone(timedelta(hours=-5)))
        earlier = datetime(2026, 11, 20, 13, tzinfo=timezone.utc)
        later = datetime(2026, 11, 20, 14, tzinfo=timezone.utc)
        provider = Mock()
        provider.fetch_hourly_forecasts.return_value = [[weather_row(earlier), weather_row(later, wind=18)]]

        results = enrich_checkpoints_with_weather([checkpoint(eta)], provider)

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["weather_data_available"])
        self.assertEqual(results[0]["weather_data_status"], "available")
        self.assertEqual(results[0]["weather_timestamp"], earlier)
        self.assertEqual(results[0]["weather_match_delta_seconds"], 1200)
        self.assertEqual(results[0]["wind_speed_mph"], 12)
        self.assertEqual(results[0]["precipitation_inches_per_hour"], 0.1)
        self.assertEqual(results[0]["snowfall_inches_per_hour"], 0)
        provider.fetch_hourly_forecasts.assert_called_once_with([{"latitude": 42.36, "longitude": -71.05}])

    def test_half_hour_tie_selects_earlier_forecast_timestamp(self):
        eta = datetime(2026, 11, 20, 8, 30, tzinfo=timezone.utc)
        earlier = datetime(2026, 11, 20, 8, tzinfo=timezone.utc)
        later = datetime(2026, 11, 20, 9, tzinfo=timezone.utc)
        provider = Mock()
        provider.fetch_hourly_forecasts.return_value = [[weather_row(earlier, wind=10), weather_row(later, wind=20)]]

        result = enrich_checkpoints_with_weather([checkpoint(eta)], provider)[0]

        self.assertEqual(result["weather_timestamp"], earlier)
        self.assertEqual(result["wind_speed_mph"], 10)
        self.assertEqual(result["weather_match_delta_seconds"], 1800)

    def test_outside_forecast_time_coverage_is_unavailable_and_never_zeroed(self):
        eta = datetime(2026, 11, 20, 10, tzinfo=timezone.utc)
        only_row = weather_row(datetime(2026, 11, 20, 8, tzinfo=timezone.utc))
        provider = Mock()
        provider.fetch_hourly_forecasts.return_value = [[only_row]]

        result = enrich_checkpoints_with_weather([checkpoint(eta)], provider)[0]

        self.assertFalse(result["weather_data_available"])
        self.assertEqual(result["weather_data_status"], "unavailable")
        self.assertIsNone(result["wind_speed_mph"])
        self.assertIsNone(result["precipitation_inches_per_hour"])
        self.assertIsNone(result["weather_timestamp"])

    def test_partial_measurements_are_incomplete_and_not_safe(self):
        eta = datetime(2026, 11, 20, 8, tzinfo=timezone.utc)
        provider = Mock()
        provider.fetch_hourly_forecasts.return_value = [[weather_row(eta, snowfall=None)]]

        result = enrich_checkpoints_with_weather([checkpoint(eta)], provider)[0]

        self.assertFalse(result["weather_data_available"])
        self.assertEqual(result["weather_data_status"], "incomplete")
        self.assertEqual(result["wind_speed_mph"], 12)
        self.assertIsNone(result["snowfall_inches_per_hour"])

    def test_malformed_weather_values_fail_closed(self):
        eta = datetime(2026, 11, 20, 8, tzinfo=timezone.utc)
        provider = Mock()
        provider.fetch_hourly_forecasts.return_value = [[weather_row(eta, wind="calm")]]

        with self.assertRaises(InvalidWeatherResponse):
            enrich_checkpoints_with_weather([checkpoint(eta)], provider)

    def test_multiple_checkpoints_keep_provider_order(self):
        first_eta = datetime(2026, 11, 20, 8, tzinfo=timezone.utc)
        second_eta = datetime(2026, 11, 20, 9, tzinfo=timezone.utc)
        provider = Mock()
        provider.fetch_hourly_forecasts.return_value = [
            [weather_row(first_eta, wind=10)], [weather_row(second_eta, wind=20)],
        ]

        results = enrich_checkpoints_with_weather([
            checkpoint(first_eta, checkpoint_id="one"),
            checkpoint(second_eta, latitude=41, checkpoint_id="two"),
        ], provider)

        self.assertEqual([row["wind_speed_mph"] for row in results], [10, 20])
        self.assertEqual([row["checkpoint_id"] for row in results], ["one", "two"])

    def test_empty_input_skips_provider_and_provider_shape_mismatch_fails(self):
        provider = Mock()
        self.assertEqual(enrich_checkpoints_with_weather([], provider), [])
        provider.fetch_hourly_forecasts.return_value = []
        with self.assertRaises(InvalidWeatherResponse):
            enrich_checkpoints_with_weather([checkpoint(datetime.now(timezone.utc))], provider)

    def test_rejects_naive_etas_and_invalid_coordinates(self):
        provider = Mock()
        with self.assertRaises(CheckpointWeatherError):
            enrich_checkpoints_with_weather([checkpoint(datetime(2026, 11, 20, 8))], provider)
        with self.assertRaises(CheckpointWeatherError):
            enrich_checkpoints_with_weather([checkpoint(datetime.now(timezone.utc), latitude=91)], provider)
        provider.fetch_hourly_forecasts.assert_not_called()
