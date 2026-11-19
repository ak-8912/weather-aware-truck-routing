from typing import Any
import math

from apps.risk_engine.services.risk_levels import NO_TRAVEL


PRIORITY_ORDER = (
    "fewest_severe_miles",
    "fewest_high_risk_miles",
    "lowest_average_risk_score",
    "shortest_travel_time",
)


def recommend_route(routes: list[dict[str, Any]]) -> dict[str, Any]:
    """Rank analyzed routes using the assessment's ordered priorities and safety gate."""
    if not routes:
        raise ValueError("At least one analyzed route is required for a recommendation.")
    route_ids = [route.get("route_id") for route in routes]
    if any(not isinstance(route_id, str) or not route_id for route_id in route_ids):
        raise ValueError("Every analyzed route must have a route ID.")
    if len(set(route_ids)) != len(route_ids):
        raise ValueError("Analyzed route IDs must be unique.")

    for route in routes:
        _ranking_key(route)
        _no_travel_miles(route)
        coverage = _finite_nonnegative(route.get("weather_coverage_percent"), "Weather coverage")
        if coverage > 100:
            raise ValueError("Weather coverage cannot exceed 100 percent.")

    has_no_travel = {route["route_id"]: _no_travel_miles(route) > 0 for route in routes}
    safe_alternatives = [route for route in routes if not has_no_travel[route["route_id"]]]
    candidates = safe_alternatives or routes
    ranked = sorted(candidates, key=_ranking_key)
    selected = ranked[0]

    all_routes_have_no_travel = not safe_alternatives
    complete_comparison = all(route.get("weather_coverage_percent") == 100 for route in routes)
    selected_coverage = float(selected.get("weather_coverage_percent", 0))
    if all_routes_have_no_travel:
        status = "no_safe_routes"
        message = (
            "Every available route has No Travel exposure. This route has the best ranking among the options, "
            "but none is suitable for travel under the assessed conditions."
        )
    elif not complete_comparison:
        status = "incomplete_weather_data"
        message = (
            f"This route ranks first using available weather data, but the comparison is incomplete. "
            f"Its weather coverage is {selected_coverage:.1f}%; missing segments are not verified as safe."
        )
    else:
        status = "recommended"
        message = "This route ranks first under the assessment's weather-risk priorities and has complete weather coverage."

    return {
        "recommended_route_id": selected["route_id"],
        "recommendation_explanation": {
            "status": status,
            "message": message,
            "reason": _ranking_reason(selected, routes, has_no_travel),
            "priority_order": list(PRIORITY_ORDER),
            "comparison_method": (
                "Routes with known No Travel exposure are screened out when any route has none; "
                "remaining routes are ranked by severe miles, high-risk miles, average observed risk, then travel time."
            ),
            "is_fully_verified": complete_comparison,
            "selected_route_safe_to_travel": bool(selected.get("safe_to_travel", False)) and not all_routes_have_no_travel,
            "no_travel_warning": all_routes_have_no_travel,
            "routes": [_comparison_row(route) for route in routes],
        },
    }


def _ranking_key(route: dict[str, Any]) -> tuple[float, float, float, float, str]:
    risk_miles = route.get("risk_miles", {})
    if not isinstance(risk_miles, dict):
        raise ValueError("Route risk miles must be provided as a mapping.")
    average = route.get("average_risk_score")
    duration = _finite_nonnegative(route.get("duration_seconds"), "Route duration")
    if duration <= 0:
        raise ValueError("Route duration must be positive.")
    if average is None:
        normalized_average = float("inf")
    else:
        normalized_average = _finite_nonnegative(average, "Average risk score")
        if not 1 <= normalized_average <= 5:
            raise ValueError("Average risk score must be between 1 and 5.")
    return (
        _finite_nonnegative(risk_miles.get("severe"), "Severe-risk miles"),
        _finite_nonnegative(risk_miles.get("high"), "High-risk miles"),
        normalized_average,
        duration,
        route["route_id"],
    )


def _no_travel_miles(route: dict[str, Any]) -> float:
    if "no_travel_exposure_miles" in route:
        return _finite_nonnegative(route["no_travel_exposure_miles"], "No Travel miles")
    return _finite_nonnegative(route.get("risk_miles", {}).get(NO_TRAVEL), "No Travel miles")


def _finite_nonnegative(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a finite non-negative number.")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a finite non-negative number.") from exc
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{label} must be a finite non-negative number.")
    return number


def _comparison_row(route: dict[str, Any]) -> dict[str, Any]:
    risk_miles = route.get("risk_miles", {})
    return {
        "route_id": route["route_id"],
        "severe_miles": float(risk_miles.get("severe", 0)),
        "high_risk_miles": float(risk_miles.get("high", 0)),
        "average_risk_score": route.get("average_risk_score"),
        "travel_time_seconds": route.get("duration_seconds"),
        "no_travel_miles": _no_travel_miles(route),
        "weather_coverage_percent": route.get("weather_coverage_percent", 0),
        "safe_to_travel": bool(route.get("safe_to_travel", False)),
    }


def _ranking_reason(selected: dict[str, Any], routes: list[dict[str, Any]], has_no_travel: dict[str, bool]) -> str:
    selected_key = _ranking_key(selected)
    safety_gate_applied = any(has_no_travel.values()) and not has_no_travel[selected["route_id"]]
    competitors = [
        route for route in routes
        if route["route_id"] != selected["route_id"]
        and (not safety_gate_applied or not has_no_travel[route["route_id"]])
    ]
    prefix = "It has no known No Travel exposure; among those alternatives, " if safety_gate_applied else ""
    if not competitors:
        if safety_gate_applied:
            return "It has no known No Travel exposure; all other routes have known No Travel miles."
        return "It is the only route returned by the routing provider."
    labels = (
        "fewest severe-risk miles",
        "fewest high-risk miles after the severe-mile comparison",
        "lowest average observed risk after severe and high-risk miles tie",
        "shortest travel time after the weather-risk metrics tie",
    )
    for index, label in enumerate(labels):
        if any(_ranking_key(other)[index] > selected_key[index] for other in competitors):
            return f"{prefix}it ranks first on {label}"
    return f"{prefix}its weather-risk and duration metrics tie with alternatives; route ID provides a stable ordering."
