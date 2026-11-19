import math
from datetime import datetime
from typing import Any

from apps.risk_engine.services.risk_calculator import RiskCalculationError, calculate_checkpoint_risk, validate_load_weight
from apps.risk_engine.services.risk_levels import (
    NO_TRAVEL,
    RISK_MILE_CATEGORIES,
    RISK_SCORE,
    UNAVAILABLE_WEATHER,
)
from apps.routing.services.checkpoint_generator import METERS_PER_MILE

DISTANCE_TOLERANCE_METERS = 1.0


def calculate_route_risk(
    route: dict[str, Any],
    checkpoints: list[dict[str, Any]],
    load_weight_lb: float,
) -> dict[str, Any]:
    """Calculate distance-weighted route risk using midpoint regions per checkpoint.

    Each checkpoint represents the route span nearest to it: half the distance to
    the previous checkpoint and half the distance to the next. The two endpoint
    checkpoints each own their terminal half-span, so represented miles sum to the
    provider's full route distance without dropping the final segment.
    """
    load = validate_load_weight(load_weight_lb)
    route_id = str(route.get("route_id", "route"))
    total_distance_meters = _positive_finite(route.get("distance_meters"), "Route distance must be positive and finite.")
    duration_seconds = _positive_finite(route.get("duration_seconds"), "Route duration must be positive and finite.")
    if not isinstance(checkpoints, list) or len(checkpoints) < 2:
        raise RiskCalculationError("At least an origin and destination checkpoint are required.")

    checkpoint_distances = []
    checkpoint_ids = set()
    for checkpoint in checkpoints:
        if not isinstance(checkpoint, dict):
            raise RiskCalculationError("Checkpoint data must be objects.")
        distance = _finite_number(checkpoint.get("distance_from_origin_meters"), "Checkpoint distance must be finite.")
        if distance < 0 or distance > total_distance_meters + DISTANCE_TOLERANCE_METERS:
            raise RiskCalculationError("Checkpoint distance must fall within the route.")
        if checkpoint_distances and distance <= checkpoint_distances[-1]:
            raise RiskCalculationError("Checkpoint distances must increase strictly along the route.")
        checkpoint_id = checkpoint.get("checkpoint_id")
        if not isinstance(checkpoint_id, str) or not checkpoint_id or checkpoint_id in checkpoint_ids:
            raise RiskCalculationError("Checkpoint IDs must be present and unique within a route.")
        checkpoint_ids.add(checkpoint_id)
        checkpoint_distances.append(distance)

    if abs(checkpoint_distances[0]) > DISTANCE_TOLERANCE_METERS:
        raise RiskCalculationError("Checkpoint list must include the route origin.")
    if abs(checkpoint_distances[-1] - total_distance_meters) > DISTANCE_TOLERANCE_METERS:
        raise RiskCalculationError("Checkpoint list must include the route destination.")

    risk_checkpoints = [calculate_checkpoint_risk(checkpoint, load) for checkpoint in checkpoints]
    boundaries = [0.0]
    boundaries.extend(
        (left + right) / 2 for left, right in zip(checkpoint_distances, checkpoint_distances[1:])
    )
    boundaries.append(total_distance_meters)

    risk_miles = {category: 0.0 for category in RISK_MILE_CATEGORIES}
    risk_miles[UNAVAILABLE_WEATHER] = 0.0
    weighted_score_mile_sum = 0.0
    covered_miles = 0.0
    known_no_travel_miles = 0.0
    maximum_risk = None

    for index, checkpoint in enumerate(risk_checkpoints):
        segment_miles = max(0.0, boundaries[index + 1] - boundaries[index]) / METERS_PER_MILE
        category = checkpoint["risk_level"] if checkpoint["weather_data_available"] else UNAVAILABLE_WEATHER
        risk_miles[category] += segment_miles
        if checkpoint["known_no_travel_exposure"]:
            known_no_travel_miles += segment_miles
            maximum_risk = NO_TRAVEL
        if category != UNAVAILABLE_WEATHER:
            covered_miles += segment_miles
            weighted_score_mile_sum += RISK_SCORE[category] * segment_miles
            if maximum_risk is None or RISK_SCORE[category] > RISK_SCORE[maximum_risk]:
                maximum_risk = category

    total_miles = total_distance_meters / METERS_PER_MILE
    weather_coverage_percent = covered_miles / total_miles * 100
    average_risk_score = weighted_score_mile_sum / covered_miles if covered_miles > 0 else None
    no_travel_miles = risk_miles[NO_TRAVEL]
    no_travel_exposure_miles = no_travel_miles + known_no_travel_miles
    has_no_travel_exposure = no_travel_exposure_miles > 0
    arrival_time = checkpoints[-1].get("estimated_arrival_time")
    if arrival_time is not None and (not isinstance(arrival_time, datetime) or arrival_time.utcoffset() is None):
        raise RiskCalculationError("Arrival time must be timezone-aware when provided.")

    return {
        "route_id": route_id,
        "distance_meters": total_distance_meters,
        "distance_miles": total_miles,
        "duration_seconds": duration_seconds,
        "total_checkpoints": len(risk_checkpoints),
        "risk_miles": {key: round(value, 6) for key, value in risk_miles.items()},
        "unavailable_weather_miles": round(risk_miles[UNAVAILABLE_WEATHER], 6),
        "known_no_travel_exposure_miles": round(known_no_travel_miles, 6),
        "no_travel_exposure_miles": round(no_travel_exposure_miles, 6),
        "average_risk_score": round(average_risk_score, 6) if average_risk_score is not None else None,
        "maximum_risk_level": maximum_risk,
        "weather_coverage_percent": round(weather_coverage_percent, 4),
        "has_no_travel_exposure": has_no_travel_exposure,
        "unsafe": has_no_travel_exposure,
        "safe_to_travel": not has_no_travel_exposure and weather_coverage_percent >= 100 - 1e-6,
        "estimated_arrival_time": arrival_time,
        "checkpoints": risk_checkpoints,
    }


def _finite_number(value: Any, message: str) -> float:
    if isinstance(value, bool):
        raise RiskCalculationError(message)
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise RiskCalculationError(message) from exc
    if not math.isfinite(number):
        raise RiskCalculationError(message)
    return number


def _positive_finite(value: Any, message: str) -> float:
    number = _finite_number(value, message)
    if number <= 0:
        raise RiskCalculationError(message)
    return number
