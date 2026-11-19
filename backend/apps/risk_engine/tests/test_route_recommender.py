import pytest

from apps.risk_engine.services.route_recommender import recommend_route


def summary(route_id, severe=0, high=0, average=1, duration=3600, no_travel=0, coverage=100):
    return {
        "route_id": route_id,
        "risk_miles": {"severe": severe, "high": high, "no_travel": no_travel},
        "no_travel_exposure_miles": no_travel,
        "average_risk_score": average,
        "duration_seconds": duration,
        "weather_coverage_percent": coverage,
        "safe_to_travel": no_travel == 0 and coverage == 100,
    }


def test_fewest_severe_miles_has_priority_over_high_risk_and_duration():
    routes = [
        summary("A", severe=1, high=20, average=4.5, duration=10_000),
        summary("B", severe=2, high=0, average=1.0, duration=3_000),
    ]

    assert recommend_route(routes)["recommended_route_id"] == "A"


def test_fewest_high_miles_is_second_priority():
    routes = [
        summary("A", severe=1, high=20, average=1.0, duration=3_000),
        summary("B", severe=1, high=10, average=4.0, duration=10_000),
    ]

    assert recommend_route(routes)["recommended_route_id"] == "B"


def test_lowest_average_risk_is_third_priority():
    routes = [
        summary("A", severe=1, high=10, average=2.7, duration=3_000),
        summary("C", severe=1, high=10, average=2.1, duration=10_000),
    ]

    assert recommend_route(routes)["recommended_route_id"] == "C"


def test_travel_time_is_fourth_priority_when_weather_metrics_tie():
    routes = [
        summary("long", severe=1, high=10, average=2.0, duration=7_200),
        summary("short", severe=1, high=10, average=2.0, duration=3_600),
    ]

    assert recommend_route(routes)["recommended_route_id"] == "short"


def test_route_with_no_travel_exposure_cannot_beat_an_alternative_without_it():
    routes = [
        summary("unsafe", severe=0, high=0, average=1, duration=1_000, no_travel=0.1),
        summary("clear", severe=20, high=30, average=5, duration=20_000, no_travel=0),
    ]

    result = recommend_route(routes)

    assert result["recommended_route_id"] == "clear"
    assert result["recommendation_explanation"]["status"] == "recommended"
    assert result["recommendation_explanation"]["selected_route_safe_to_travel"] is True


def test_when_every_route_has_no_travel_exposure_returns_unsafe_route_with_warning():
    routes = [
        summary("unsafe-a", severe=4, high=2, average=3, duration=1_000, no_travel=4),
        summary("unsafe-b", severe=2, high=2, average=4, duration=2_000, no_travel=1),
    ]

    result = recommend_route(routes)
    explanation = result["recommendation_explanation"]

    assert result["recommended_route_id"] == "unsafe-b"
    assert explanation["status"] == "no_safe_routes"
    assert explanation["no_travel_warning"] is True
    assert explanation["selected_route_safe_to_travel"] is False
    assert "none is suitable for travel" in explanation["message"]


def test_incomplete_weather_comparison_is_disclosed_and_not_marked_safe():
    routes = [summary("partial", severe=0, high=0, average=1, duration=3_600, coverage=60),
              summary("full", severe=1, high=1, average=2, duration=4_000, coverage=100)]

    result = recommend_route(routes)
    explanation = result["recommendation_explanation"]

    assert result["recommended_route_id"] == "partial"
    assert explanation["status"] == "incomplete_weather_data"
    assert explanation["is_fully_verified"] is False
    assert explanation["selected_route_safe_to_travel"] is False
    assert "missing segments are not verified as safe" in explanation["message"]
    assert {"severe_miles", "high_risk_miles", "average_risk_score", "travel_time_seconds",
            "no_travel_miles", "weather_coverage_percent"}.issubset(explanation["routes"][0])


def test_empty_or_duplicate_route_sets_are_rejected():
    with pytest.raises(ValueError):
        recommend_route([])
    with pytest.raises(ValueError):
        recommend_route([summary("duplicate"), summary("duplicate")])
