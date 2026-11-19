import math
from typing import Any

from apps.risk_engine.services.load_rules import load_adjusted_wind_risk
from apps.risk_engine.services.risk_levels import (
    HIGH,
    LOW,
    MODERATE,
    NO_TRAVEL,
    RISK_SEVERITY,
    SEVERE,
)


class RiskCalculationError(ValueError):
    """Raised when risk inputs are invalid or missing required trip data."""


def classify_wind_risk(wind_speed_mph: float | None) -> str | None:
    value = _measurement(wind_speed_mph, "Wind speed")
    if value is None:
        return None
    if value < 25:
        return LOW
    if value < 35:
        return MODERATE
    if value < 45:
        return HIGH
    if value < 55:
        return SEVERE
    return NO_TRAVEL


def classify_rain_risk(rain_inches_per_hour: float | None) -> str | None:
    value = _measurement(rain_inches_per_hour, "Rain intensity")
    if value is None:
        return None
    if value < 0.10:
        return LOW
    if value < 0.25:
        return MODERATE
    if value < 0.50:
        return HIGH
    if value <= 1.00:
        return SEVERE
    return NO_TRAVEL


def classify_snow_risk(snow_inches_per_hour: float | None) -> str | None:
    value = _measurement(snow_inches_per_hour, "Snowfall intensity")
    if value is None:
        return None
    if value < 0.5:
        return LOW
    if value < 1.0:
        return MODERATE
    if value < 2.0:
        return HIGH
    if value <= 3.0:
        return SEVERE
    return NO_TRAVEL


def calculate_checkpoint_risk(checkpoint: dict[str, Any], load_weight_lb: float) -> dict[str, Any]:
    """Return individual weather classes and the final load-adjusted checkpoint risk."""
    load = validate_load_weight(load_weight_lb)
    wind_value = _measurement(checkpoint.get("wind_speed_mph"), "Wind speed")
    rain_value = _measurement(checkpoint.get("precipitation_inches_per_hour"), "Rain intensity")
    snow_value = _measurement(checkpoint.get("snowfall_inches_per_hour"), "Snowfall intensity")

    wind_risk = classify_wind_risk(wind_value)
    rain_risk = classify_rain_risk(rain_value)
    snow_risk = classify_snow_risk(snow_value)
    adjusted_wind_risk = (
        load_adjusted_wind_risk(wind_value, load, wind_risk) if wind_value is not None else None
    )

    all_measurements_present = all(value is not None for value in (wind_value, rain_value, snow_value))
    declared_available = checkpoint.get("weather_data_available")
    declared_status = checkpoint.get("weather_data_status")
    available = all_measurements_present and declared_available is not False and declared_status not in {
        "unavailable", "incomplete"
    }

    base_risk = _most_severe(risk for risk in (wind_risk, rain_risk, snow_risk) if risk is not None)
    observed_risk = _most_severe(risk for risk in (base_risk, adjusted_wind_risk) if risk is not None)
    # Even with another missing measurement, a known No Travel condition remains
    # a real hazard and must not disappear into the unavailable-data bucket.
    final_risk = observed_risk if available or observed_risk == NO_TRAVEL else None
    status = "available" if available else (declared_status if declared_status in {"unavailable", "incomplete"} else "incomplete")

    return {
        **checkpoint,
        "wind_risk": wind_risk,
        "rain_risk": rain_risk,
        "snow_risk": snow_risk,
        "base_weather_risk": base_risk if available else None,
        "observed_weather_risk": observed_risk,
        "load_adjusted_wind_risk": adjusted_wind_risk,
        "risk_level": final_risk,
        "risk_score": RISK_SEVERITY[final_risk] if available and final_risk is not None else None,
        "known_no_travel_exposure": not available and observed_risk == NO_TRAVEL,
        "weather_data_available": available,
        "weather_data_status": status,
    }


def _measurement(value: Any, label: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise RiskCalculationError(f"{label} must be a non-negative finite number.")
    try:
        normalized = float(value)
    except (TypeError, ValueError) as exc:
        raise RiskCalculationError(f"{label} must be a non-negative finite number.") from exc
    if not math.isfinite(normalized) or normalized < 0:
        raise RiskCalculationError(f"{label} must be a non-negative finite number.")
    return normalized


def validate_load_weight(value: Any) -> float:
    if isinstance(value, bool):
        raise RiskCalculationError("Load weight must be a non-negative finite number of pounds.")
    try:
        normalized = float(value)
    except (TypeError, ValueError) as exc:
        raise RiskCalculationError("Load weight must be a non-negative finite number of pounds.") from exc
    if not math.isfinite(normalized) or normalized < 0:
        raise RiskCalculationError("Load weight must be a non-negative finite number of pounds.")
    return normalized


def _most_severe(risks):
    return max(risks, key=RISK_SEVERITY.__getitem__, default=None)
