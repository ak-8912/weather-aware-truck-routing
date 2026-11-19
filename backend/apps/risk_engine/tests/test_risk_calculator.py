from datetime import datetime, timezone

import pytest

from apps.risk_engine.services.risk_calculator import (
    RiskCalculationError,
    calculate_checkpoint_risk,
    classify_rain_risk,
    classify_snow_risk,
    classify_wind_risk,
)
from apps.risk_engine.services.risk_levels import HIGH, LOW, MODERATE, NO_TRAVEL, SEVERE


@pytest.mark.parametrize("wind, expected", [
    (24.9, LOW), (25, MODERATE), (34, MODERATE), (35, HIGH),
    (44, HIGH), (45, SEVERE), (54.9, SEVERE), (55, NO_TRAVEL),
])
def test_wind_classification_boundaries(wind, expected):
    assert classify_wind_risk(wind) == expected


@pytest.mark.parametrize("rain, expected", [
    (0.09, LOW), (0.10, MODERATE), (0.24, MODERATE), (0.25, HIGH),
    (0.49, HIGH), (0.50, SEVERE), (1.00, SEVERE), (1.01, NO_TRAVEL),
])
def test_rain_classification_boundaries(rain, expected):
    assert classify_rain_risk(rain) == expected


@pytest.mark.parametrize("snow, expected", [
    (0.49, LOW), (0.50, MODERATE), (0.99, MODERATE), (1.00, HIGH),
    (1.99, HIGH), (2.00, SEVERE), (3.00, SEVERE), (3.01, NO_TRAVEL),
])
def test_snow_classification_boundaries(snow, expected):
    assert classify_snow_risk(snow) == expected


def checkpoint(wind=10, rain=0, snow=0, status="available", available=True):
    return {
        "checkpoint_id": "route:checkpoint:1",
        "latitude": 42,
        "longitude": -71,
        "estimated_arrival_time": datetime(2026, 11, 20, 8, tzinfo=timezone.utc),
        "wind_speed_mph": wind,
        "precipitation_inches_per_hour": rain,
        "snowfall_inches_per_hour": snow,
        "weather_data_status": status,
        "weather_data_available": available,
    }


def test_combined_weather_risk_uses_the_most_severe_weather_condition():
    result = calculate_checkpoint_risk(checkpoint(wind=25, rain=0.25, snow=1), 20_000)

    assert result["wind_risk"] == MODERATE
    assert result["rain_risk"] == HIGH
    assert result["snow_risk"] == HIGH
    assert result["base_weather_risk"] == HIGH
    assert result["risk_level"] == HIGH


@pytest.mark.parametrize("wind, load, expected", [
    (45, 30_000, SEVERE),
    (45, 30_001, NO_TRAVEL),
    (54, 30_001, NO_TRAVEL),
    (35, 40_000, HIGH),
    (35, 40_001, SEVERE),
    (44, 40_001, SEVERE),
    (55, 0, NO_TRAVEL),
    (35, 30_001, HIGH),
])
def test_load_specific_wind_rules_at_assessment_boundaries(wind, load, expected):
    result = calculate_checkpoint_risk(checkpoint(wind=wind), load)
    assert result["load_adjusted_wind_risk"] == expected
    assert result["risk_level"] == expected


def test_load_rules_do_not_adjust_rain_or_snow_classification():
    result = calculate_checkpoint_risk(checkpoint(wind=20, rain=0.25, snow=0), 50_000)

    assert result["rain_risk"] == HIGH
    assert result["load_adjusted_wind_risk"] == LOW
    assert result["risk_level"] == HIGH


def test_missing_weather_is_unavailable_but_known_no_travel_wind_remains_unsafe():
    result = calculate_checkpoint_risk(
        checkpoint(wind=55, rain=None, snow=None, status="incomplete", available=False),
        25_000,
    )

    assert result["weather_data_available"] is False
    assert result["risk_level"] == NO_TRAVEL
    assert result["risk_score"] is None
    assert result["known_no_travel_exposure"] is True


@pytest.mark.parametrize("wind, load", [(-0.01, 0), (float("inf"), 0), (10, -1), (True, 1)])
def test_invalid_measurements_and_loads_are_rejected(wind, load):
    with pytest.raises(RiskCalculationError):
        calculate_checkpoint_risk(checkpoint(wind=wind), load)


def test_individual_classifiers_keep_missing_values_missing():
    assert classify_wind_risk(None) is None
    assert classify_rain_risk(None) is None
    assert classify_snow_risk(None) is None
