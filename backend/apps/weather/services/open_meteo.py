import logging
import math
from datetime import datetime, timezone
from typing import Any

import requests
from django.conf import settings
from django.core.cache import cache

from apps.weather.services.weather_provider import (
    InvalidWeatherResponse,
    WeatherProvider,
    WeatherProviderRateLimited,
    WeatherProviderTimeout,
    WeatherProviderUnavailable,
)

logger = logging.getLogger(__name__)

WIND_KMH_TO_MPH = 0.621371
MM_TO_INCH = 1 / 25.4
CM_TO_INCH = 1 / 2.54
HOURLY_VARIABLES = ("wind_speed_10m", "precipitation", "snowfall")


class OpenMeteoProvider(WeatherProvider):
    BATCH_SIZE = 50

    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self.url = getattr(settings, "OPEN_METEO_BASE_URL", "https://api.open-meteo.com/v1/forecast")
        self.timeout = getattr(settings, "OPEN_METEO_TIMEOUT", 15)
        self.cache_seconds = getattr(settings, "OPEN_METEO_CACHE_SECONDS", 1800)

    def fetch_hourly_forecasts(self, locations: list[dict[str, float]]) -> list[list[dict[str, Any]]]:
        if not locations:
            return []

        cache_keys = [_location_cache_key(location) for location in locations]
        unique_locations: dict[str, dict[str, float]] = {}
        for key, location in zip(cache_keys, locations):
            unique_locations.setdefault(key, location)

        cached = cache.get_many([f"openmeteo:v1:{key}" for key in unique_locations])
        unresolved = [
            (key, location) for key, location in unique_locations.items()
            if f"openmeteo:v1:{key}" not in cached
        ]
        fetched: dict[str, list[dict[str, Any]]] = {}
        for offset in range(0, len(unresolved), self.BATCH_SIZE):
            batch = unresolved[offset:offset + self.BATCH_SIZE]
            responses = self._fetch_batch([location for _, location in batch])
            for (key, _), payload in zip(batch, responses):
                rows = normalize_hourly_forecast(payload)
                fetched[key] = rows
                cache.set(f"openmeteo:v1:{key}", rows, timeout=self.cache_seconds)

        forecasts_by_key = {}
        for key in unique_locations:
            forecast_key = f"openmeteo:v1:{key}"
            if forecast_key in cached:
                forecasts_by_key[key] = cached[forecast_key]
            else:
                forecasts_by_key[key] = fetched[key]
        return [forecasts_by_key[key] for key in cache_keys]

    def _fetch_batch(self, locations: list[dict[str, float]]) -> list[dict[str, Any]]:
        params = {
            "latitude": ",".join(f"{location['latitude']:.5f}" for location in locations),
            "longitude": ",".join(f"{location['longitude']:.5f}" for location in locations),
            "hourly": ",".join(HOURLY_VARIABLES),
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
            "timezone": "UTC",
            "timeformat": "unixtime",
            "forecast_days": 16,
        }
        try:
            response = self.session.get(self.url, params=params, timeout=self.timeout)
        except requests.Timeout as exc:
            logger.warning("Open-Meteo request timed out", extra={"event": "openmeteo_timeout"})
            raise WeatherProviderTimeout() from exc
        except requests.RequestException as exc:
            logger.warning("Open-Meteo request failed", extra={"event": "openmeteo_request_failed"})
            raise WeatherProviderUnavailable() from exc

        if response.status_code == 429:
            raise WeatherProviderRateLimited()
        if not 200 <= response.status_code < 300:
            logger.warning("Open-Meteo returned an error", extra={"event": "openmeteo_http_error", "status": response.status_code})
            raise WeatherProviderUnavailable()
        try:
            payload = response.json()
        except (ValueError, requests.JSONDecodeError) as exc:
            raise InvalidWeatherResponse() from exc
        if isinstance(payload, dict) and payload.get("error"):
            raise WeatherProviderUnavailable()
        if len(locations) == 1 and isinstance(payload, dict):
            payloads = [payload]
        elif isinstance(payload, list):
            payloads = payload
        else:
            raise InvalidWeatherResponse()
        if len(payloads) != len(locations) or not all(isinstance(item, dict) for item in payloads):
            raise InvalidWeatherResponse()
        return payloads


def normalize_hourly_forecast(payload: dict[str, Any]) -> list[dict[str, Any]]:
    hourly = payload.get("hourly")
    units = payload.get("hourly_units")
    if not isinstance(hourly, dict) or not isinstance(units, dict):
        raise InvalidWeatherResponse()
    timestamps = hourly.get("time")
    if not isinstance(timestamps, list):
        raise InvalidWeatherResponse()

    values = {}
    for variable in HOURLY_VARIABLES:
        raw_values = hourly.get(variable)
        if raw_values is None:
            values[variable] = [None] * len(timestamps)
            continue
        if not isinstance(raw_values, list) or len(raw_values) != len(timestamps):
            raise InvalidWeatherResponse()
        unit = units.get(variable)
        if not isinstance(unit, str):
            raise InvalidWeatherResponse()
        values[variable] = [_normalize_value(variable, value, unit) for value in raw_values]

    rows = []
    previous_timestamp = None
    for index, timestamp in enumerate(timestamps):
        try:
            parsed_timestamp = datetime.fromtimestamp(float(timestamp), tz=timezone.utc)
        except (TypeError, ValueError, OverflowError, OSError) as exc:
            raise InvalidWeatherResponse() from exc
        if previous_timestamp is not None and parsed_timestamp <= previous_timestamp:
            raise InvalidWeatherResponse()
        previous_timestamp = parsed_timestamp
        rows.append({
            "timestamp": parsed_timestamp,
            "wind_speed_mph": values["wind_speed_10m"][index],
            "precipitation_inches_per_hour": values["precipitation"][index],
            "snowfall_inches_per_hour": values["snowfall"][index],
        })
    return rows


def _normalize_value(variable: str, value: Any, unit: str) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise InvalidWeatherResponse() from exc
    if not math.isfinite(number) or number < 0:
        raise InvalidWeatherResponse()

    normalized_unit = unit.strip().casefold().replace(" ", "")
    if variable == "wind_speed_10m":
        if normalized_unit in {"mph", "mi/h"}:
            return number
        if normalized_unit in {"km/h", "kmh"}:
            return number * WIND_KMH_TO_MPH
        if normalized_unit in {"m/s", "ms"}:
            return number * 2.2369362921
        if normalized_unit in {"kn", "kt", "knots"}:
            return number * 1.150779448
    elif variable == "precipitation":
        if normalized_unit in {"inch", "in"}:
            return number
        if normalized_unit in {"mm", "millimeter", "millimeters"}:
            return number * MM_TO_INCH
    elif variable == "snowfall":
        if normalized_unit in {"inch", "in"}:
            return number
        if normalized_unit in {"cm", "centimeter", "centimeters"}:
            return number * CM_TO_INCH
        if normalized_unit in {"mm", "millimeter", "millimeters"}:
            return number * MM_TO_INCH
    raise InvalidWeatherResponse()


def _location_cache_key(location: dict[str, float]) -> str:
    try:
        latitude = float(location["latitude"])
        longitude = float(location["longitude"])
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidWeatherResponse() from exc
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise InvalidWeatherResponse()
    return f"{latitude:.4f}:{longitude:.4f}"
