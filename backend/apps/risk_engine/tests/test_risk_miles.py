from datetime import datetime, timedelta, timezone

import pytest

from apps.risk_engine.services.risk_calculator import RiskCalculationError
from apps.risk_engine.services.risk_levels import HIGH, LOW, NO_TRAVEL, SEVERE, UNAVAILABLE_WEATHER
from apps.risk_engine.services.risk_miles import calculate_route_risk
from apps.routing.services.checkpoint_generator import METERS_PER_MILE


DEPARTURE = datetime(2026, 11, 20, 8, tzinfo=timezone.utc)


def checkpoint(index, distance_miles, wind=10, rain=0, snow=0, status="available", available=True):
    return {
        "checkpoint_id": f"route:checkpoint:{index}",
        "distance_from_origin_meters": distance_miles * METERS_PER_MILE,
        "estimated_arrival_time": DEPARTURE + timedelta(minutes=index * 30),
        "latitude": 42,
        "longitude": -71,
        "wind_speed_mph": wind,
        "precipitation_inches_per_hour": rain,
        "snowfall_inches_per_hour": snow,
        "weather_data_status": status,
        "weather_data_available": available,
    }


def route(distance_miles):
    return {
        "route_id": "route",
        "distance_meters": distance_miles * METERS_PER_MILE,
        "duration_seconds": 7200,
    }


def test_risk_miles_cover_full_route_and_weight_average_by_distance():
    summary = calculate_route_risk(route(50), [
        checkpoint(1, 0, wind=10),
        checkpoint(2, 25, wind=45),
        checkpoint(3, 50, wind=55),
    ], 0)

    assert summary["risk_miles"][LOW] == pytest.approx(12.5)
    assert summary["risk_miles"][SEVERE] == pytest.approx(25)
    assert summary["risk_miles"][NO_TRAVEL] == pytest.approx(12.5)
    assert sum(summary["risk_miles"].values()) == pytest.approx(50)
    assert summary["average_risk_score"] == pytest.approx(3.5)
    assert summary["weather_coverage_percent"] == pytest.approx(100)
    assert summary["maximum_risk_level"] == NO_TRAVEL
    assert summary["unsafe"] is True
    assert summary["safe_to_travel"] is False
    assert summary["estimated_arrival_time"] == DEPARTURE + timedelta(minutes=90)


def test_missing_weather_becomes_unavailable_weather_miles_not_low_miles():
    summary = calculate_route_risk(route(50), [
        checkpoint(1, 0, wind=10),
        checkpoint(2, 25, wind=10, rain=None, status="incomplete", available=False),
        checkpoint(3, 50, wind=35),
    ], 0)

    assert summary["risk_miles"][LOW] == pytest.approx(12.5)
    assert summary["risk_miles"][HIGH] == pytest.approx(12.5)
    assert summary["risk_miles"][UNAVAILABLE_WEATHER] == pytest.approx(25)
    assert summary["unavailable_weather_miles"] == pytest.approx(25)
    assert summary["weather_coverage_percent"] == pytest.approx(50)
    assert summary["average_risk_score"] == pytest.approx(2)
    assert summary["safe_to_travel"] is False


def test_known_no_travel_in_partial_weather_stays_unsafe_and_reports_unknown_miles():
    summary = calculate_route_risk(route(50), [
        checkpoint(1, 0),
        checkpoint(2, 25, wind=55, rain=None, snow=None, status="incomplete", available=False),
        checkpoint(3, 50),
    ], 0)

    assert summary["risk_miles"][UNAVAILABLE_WEATHER] == pytest.approx(25)
    assert summary["risk_miles"][LOW] == pytest.approx(25)
    assert summary["known_no_travel_exposure_miles"] == pytest.approx(25)
    assert summary["no_travel_exposure_miles"] == pytest.approx(25)
    assert summary["has_no_travel_exposure"] is True
    assert summary["maximum_risk_level"] == NO_TRAVEL
    assert summary["unsafe"] is True
    assert summary["safe_to_travel"] is False


@pytest.mark.parametrize("bad_checkpoints", [
    [],
    [checkpoint(1, 0)],
    [checkpoint(1, 1), checkpoint(2, 50)],
    [checkpoint(1, 0), checkpoint(2, 49)],
    [checkpoint(1, 0), checkpoint(2, 0), checkpoint(3, 50)],
])
def test_invalid_checkpoint_coverage_is_rejected(bad_checkpoints):
    with pytest.raises(RiskCalculationError):
        calculate_route_risk(route(50), bad_checkpoints, 0)


def test_route_summary_downgrades_claimed_available_checkpoints_with_missing_fields():
    bad = checkpoint(2, 25, rain=None, available=True)
    summary = calculate_route_risk(route(50), [checkpoint(1, 0), bad, checkpoint(3, 50)], 0)

    assert summary["weather_coverage_percent"] == pytest.approx(50)
    assert summary["risk_miles"][UNAVAILABLE_WEATHER] == pytest.approx(25)
