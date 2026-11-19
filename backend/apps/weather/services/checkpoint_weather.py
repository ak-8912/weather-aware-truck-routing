from datetime import datetime, timedelta, timezone
import math
from typing import Any

from apps.weather.services.open_meteo import OpenMeteoProvider
from apps.weather.services.weather_provider import InvalidWeatherResponse, WeatherProvider

MAX_WEATHER_MATCH_DELTA = timedelta(minutes=30)
WEATHER_FIELDS = (
    "wind_speed_mph",
    "precipitation_inches_per_hour",
    "snowfall_inches_per_hour",
)


class CheckpointWeatherError(ValueError):
    """Raised when checkpoint coordinates or ETA cannot be weather matched."""


def enrich_checkpoints_with_weather(
    checkpoints: list[dict[str, Any]],
    provider: WeatherProvider | None = None,
) -> list[dict[str, Any]]:
    """Attach the nearest hourly forecast to each checkpoint, preserving missing data."""
    if not checkpoints:
        return []
    locations = []
    for checkpoint in checkpoints:
        try:
            latitude = float(checkpoint["latitude"])
            longitude = float(checkpoint["longitude"])
            eta = checkpoint["estimated_arrival_time"]
        except (KeyError, TypeError, ValueError) as exc:
            raise CheckpointWeatherError("Checkpoint coordinates and ETA are required.") from exc
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            raise CheckpointWeatherError("Checkpoint coordinates are outside valid ranges.")
        if not isinstance(eta, datetime) or eta.utcoffset() is None:
            raise CheckpointWeatherError("Checkpoint ETA must include a timezone.")
        locations.append({"latitude": latitude, "longitude": longitude})

    forecasts = (provider or OpenMeteoProvider()).fetch_hourly_forecasts(locations)
    if len(forecasts) != len(checkpoints):
        raise InvalidWeatherResponse()

    enriched = []
    for checkpoint, hourly_rows in zip(checkpoints, forecasts):
        eta = checkpoint["estimated_arrival_time"].astimezone(timezone.utc)
        matched = _match_forecast_row(hourly_rows, eta)
        if matched is None:
            weather_fields = {field: None for field in WEATHER_FIELDS}
            enriched.append({
                **checkpoint,
                **weather_fields,
                "weather_timestamp": None,
                "weather_match_delta_seconds": None,
                "weather_data_status": "unavailable",
                "weather_data_available": False,
            })
            continue

        delta = abs((matched["timestamp"] - eta).total_seconds())
        fields = {field: matched.get(field) for field in WEATHER_FIELDS}
        for value in fields.values():
            if value is not None and (
                not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0
            ):
                raise InvalidWeatherResponse()
        available = all(value is not None for value in fields.values())
        enriched.append({
            **checkpoint,
            **fields,
            "weather_timestamp": matched["timestamp"],
            "weather_match_delta_seconds": delta,
            "weather_data_status": "available" if available else "incomplete",
            "weather_data_available": available,
        })
    return enriched


def _match_forecast_row(hourly_rows: list[dict[str, Any]], eta: datetime) -> dict[str, Any] | None:
    if not isinstance(hourly_rows, list) or not hourly_rows:
        return None
    candidates = []
    for row in hourly_rows:
        if not isinstance(row, dict) or not isinstance(row.get("timestamp"), datetime):
            raise InvalidWeatherResponse()
        timestamp = row["timestamp"]
        if timestamp.utcoffset() is None:
            raise InvalidWeatherResponse()
        candidates.append(row)
    # min() preserves source order on ties, so a half-hour tie selects the earlier hour.
    closest = min(candidates, key=lambda row: abs((row["timestamp"] - eta).total_seconds()))
    if abs(closest["timestamp"] - eta) > MAX_WEATHER_MATCH_DELTA:
        return None
    return closest
