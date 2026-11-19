from datetime import datetime, timezone
from unittest.mock import Mock

import requests
from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from apps.weather.services.open_meteo import OpenMeteoProvider, normalize_hourly_forecast
from apps.weather.services.weather_provider import (
    InvalidWeatherResponse,
    WeatherProviderRateLimited,
    WeatherProviderTimeout,
)


def forecast_payload(times=None, wind=(10.0, 20.0), precip=(0.1, 0.2), snow=(0.0, 0.05)):
    times = times or [int(datetime(2026, 11, 20, hour, tzinfo=timezone.utc).timestamp()) for hour in (8, 9)]
    return {
        "hourly": {
            "time": times,
            "wind_speed_10m": list(wind),
            "precipitation": list(precip),
            "snowfall": list(snow),
        },
        "hourly_units": {"wind_speed_10m": "mph", "precipitation": "inch", "snowfall": "inch"},
    }


class OpenMeteoTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    @override_settings(
        OPEN_METEO_BASE_URL="https://weather.example/v1/forecast",
        OPEN_METEO_TIMEOUT=7,
        OPEN_METEO_CACHE_SECONDS=120,
    )
    def test_requests_batched_hourly_variables_in_internal_units_and_caches_locations(self):
        response = Mock(status_code=200)
        response.json.return_value = [forecast_payload(), forecast_payload()]
        session = Mock()
        session.get.return_value = response
        provider = OpenMeteoProvider(session=session)
        locations = [{"latitude": 42.3, "longitude": -71.1}, {"latitude": 42.4, "longitude": -71.2}]

        forecasts = provider.fetch_hourly_forecasts(locations)
        cached_forecasts = provider.fetch_hourly_forecasts(locations)

        self.assertEqual(len(forecasts), 2)
        self.assertEqual(forecasts, cached_forecasts)
        self.assertEqual(forecasts[0][0]["wind_speed_mph"], 10)
        self.assertEqual(forecasts[0][0]["precipitation_inches_per_hour"], 0.1)
        args, kwargs = session.get.call_args
        self.assertEqual(args, ("https://weather.example/v1/forecast",))
        self.assertEqual(kwargs["params"]["latitude"], "42.30000,42.40000")
        self.assertEqual(kwargs["params"]["longitude"], "-71.10000,-71.20000")
        self.assertEqual(kwargs["params"]["hourly"], "wind_speed_10m,precipitation,snowfall")
        self.assertEqual(kwargs["params"]["wind_speed_unit"], "mph")
        self.assertEqual(kwargs["params"]["precipitation_unit"], "inch")
        self.assertEqual(kwargs["params"]["timezone"], "UTC")
        self.assertEqual(kwargs["params"]["timeformat"], "unixtime")
        self.assertEqual(kwargs["params"]["forecast_days"], 16)
        self.assertEqual(kwargs["timeout"], 7)
        session.get.assert_called_once()

    def test_deduplicates_identical_locations_within_batch(self):
        response = Mock(status_code=200)
        response.json.return_value = forecast_payload()
        session = Mock()
        session.get.return_value = response

        forecasts = OpenMeteoProvider(session=session).fetch_hourly_forecasts([
            {"latitude": 42.3, "longitude": -71.1},
            {"latitude": 42.3, "longitude": -71.1},
        ])

        self.assertEqual(forecasts[0], forecasts[1])
        session.get.assert_called_once()

    def test_splits_large_location_sets_into_bounded_batches(self):
        session = Mock()
        session.get.side_effect = [
            Mock(status_code=200, **{"json.return_value": [forecast_payload(), forecast_payload()]}),
            Mock(status_code=200, **{"json.return_value": forecast_payload()}),
        ]
        provider = OpenMeteoProvider(session=session)
        provider.BATCH_SIZE = 2
        locations = [
            {"latitude": 42.0 + index * 0.01, "longitude": -71.0}
            for index in range(3)
        ]

        forecasts = provider.fetch_hourly_forecasts(locations)

        self.assertEqual(len(forecasts), 3)
        self.assertEqual(session.get.call_count, 2)
        self.assertEqual(session.get.call_args_list[0].kwargs["params"]["latitude"], "42.00000,42.01000")
        self.assertEqual(session.get.call_args_list[1].kwargs["params"]["latitude"], "42.02000")

    def test_converts_unexpected_units_once_and_preserves_missing_measurements(self):
        payload = forecast_payload(wind=(100, None), precip=(2.54, None), snow=(2.54, None))
        payload["hourly_units"] = {"wind_speed_10m": "km/h", "precipitation": "mm", "snowfall": "cm"}

        rows = normalize_hourly_forecast(payload)

        self.assertAlmostEqual(rows[0]["wind_speed_mph"], 62.1371)
        self.assertAlmostEqual(rows[0]["precipitation_inches_per_hour"], 0.1)
        self.assertAlmostEqual(rows[0]["snowfall_inches_per_hour"], 1.0)
        self.assertIsNone(rows[1]["wind_speed_mph"])
        self.assertIsNone(rows[1]["precipitation_inches_per_hour"])
        self.assertIsNone(rows[1]["snowfall_inches_per_hour"])
        self.assertEqual(rows[0]["timestamp"], datetime(2026, 11, 20, 8, tzinfo=timezone.utc))

    def test_accepts_open_meteos_returned_miles_per_hour_unit_symbol(self):
        payload = forecast_payload(wind=(3.3, 3.7))
        payload["hourly_units"]["wind_speed_10m"] = "mp/h"

        rows = normalize_hourly_forecast(payload)

        self.assertEqual(rows[0]["wind_speed_mph"], 3.3)
        self.assertEqual(rows[1]["wind_speed_mph"], 3.7)

    def test_missing_variable_is_retained_as_missing_not_zero(self):
        payload = forecast_payload()
        del payload["hourly"]["snowfall"]

        rows = normalize_hourly_forecast(payload)

        self.assertIsNone(rows[0]["snowfall_inches_per_hour"])

    def test_invalid_units_or_mismatched_hour_arrays_fail_closed(self):
        payload = forecast_payload()
        payload["hourly_units"]["wind_speed_10m"] = "beaufort"
        with self.assertRaises(InvalidWeatherResponse):
            normalize_hourly_forecast(payload)

        payload = forecast_payload()
        payload["hourly"]["snowfall"] = [0.1]
        with self.assertRaises(InvalidWeatherResponse):
            normalize_hourly_forecast(payload)

    def test_timeout_and_rate_limit_are_translated(self):
        location = [{"latitude": 42.3, "longitude": -71.1}]
        timeout_session = Mock()
        timeout_session.get.side_effect = requests.Timeout()
        with self.assertRaises(WeatherProviderTimeout):
            OpenMeteoProvider(session=timeout_session).fetch_hourly_forecasts(location)

        cache.clear()
        limited_response = Mock(status_code=429)
        limited_session = Mock()
        limited_session.get.return_value = limited_response
        with self.assertRaises(WeatherProviderRateLimited):
            OpenMeteoProvider(session=limited_session).fetch_hourly_forecasts(location)

