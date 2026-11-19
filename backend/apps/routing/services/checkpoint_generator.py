"""Generate distance-based forecast checkpoints on a provider route geometry."""

import math
from bisect import bisect_right
from datetime import datetime, timedelta
from typing import Any

EARTH_RADIUS_METERS = 6_371_008.8
METERS_PER_MILE = 1_609.344
SUPPORTED_INTERVALS_MILES = frozenset({10, 25, 50})
DISTANCE_EPSILON_METERS = 0.01


class CheckpointGenerationError(ValueError):
    """Raised when route inputs cannot produce meaningful checkpoints."""


def generate_weather_checkpoints(
    route: dict[str, Any],
    departure_datetime: datetime,
    sampling_interval_miles: int,
) -> list[dict[str, Any]]:
    """Interpolate checkpoints along the route and calculate their ETAs.

    The provider's route distance is used for displayed cumulative distance and ETA
    proportions. Geometry segment lengths determine where each point is placed;
    their proportions are scaled to the provider's route distance to account for
    differences between polyline geodesics and the routing engine's distance.
    """
    if sampling_interval_miles not in SUPPORTED_INTERVALS_MILES:
        raise CheckpointGenerationError("Sampling interval must be 10, 25, or 50 miles.")
    if not isinstance(departure_datetime, datetime) or departure_datetime.utcoffset() is None:
        raise CheckpointGenerationError("Departure datetime must include a timezone.")

    route_id = str(route.get("route_id", "route"))
    provider_distance = _positive_finite(route.get("distance_meters"), "Route distance must be positive and finite.")
    duration_seconds = _positive_finite(route.get("duration_seconds"), "Route duration must be positive and finite.")
    coordinates = _validated_coordinates(route.get("geometry"))

    cumulative_geometry_distances = [0.0]
    for first, second in zip(coordinates, coordinates[1:]):
        cumulative_geometry_distances.append(
            cumulative_geometry_distances[-1] + _haversine_distance_meters(first, second)
        )
    geometry_distance = cumulative_geometry_distances[-1]
    if geometry_distance <= DISTANCE_EPSILON_METERS:
        raise CheckpointGenerationError("Route geometry must have a positive length.")

    interval_meters = sampling_interval_miles * METERS_PER_MILE
    target_distances = [0.0]
    interval_count = int(provider_distance // interval_meters)
    for interval_index in range(1, interval_count + 1):
        target = interval_index * interval_meters
        if target < provider_distance - DISTANCE_EPSILON_METERS:
            target_distances.append(target)
        elif abs(target - provider_distance) <= DISTANCE_EPSILON_METERS:
            target_distances.append(provider_distance)
    if len(target_distances) == 1 or abs(target_distances[-1] - provider_distance) > DISTANCE_EPSILON_METERS:
        target_distances.append(provider_distance)
    else:
        target_distances[-1] = provider_distance

    checkpoints = []
    for index, provider_distance_at_checkpoint in enumerate(target_distances):
        geometry_distance_at_checkpoint = (
            provider_distance_at_checkpoint / provider_distance * geometry_distance
        )
        longitude, latitude = _interpolate_at_distance(
            coordinates, cumulative_geometry_distances, geometry_distance_at_checkpoint
        )
        miles_from_origin = provider_distance_at_checkpoint / METERS_PER_MILE
        eta = departure_datetime + timedelta(
            seconds=duration_seconds * provider_distance_at_checkpoint / provider_distance
        )
        checkpoints.append({
            "checkpoint_id": f"{route_id}:checkpoint:{index + 1}",
            "latitude": latitude,
            "longitude": longitude,
            "distance_from_origin_meters": provider_distance_at_checkpoint,
            "distance_from_origin_miles": miles_from_origin,
            "estimated_arrival_time": eta,
        })
    return checkpoints


def _validated_coordinates(value: Any) -> list[tuple[float, float]]:
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        raise CheckpointGenerationError("Route geometry must contain at least two coordinates.")
    coordinates = []
    for coordinate in value:
        if not isinstance(coordinate, (list, tuple)) or len(coordinate) < 2:
            raise CheckpointGenerationError("Route geometry contains an invalid coordinate.")
        longitude = _finite_number(coordinate[0], "Route geometry contains an invalid longitude.")
        latitude = _finite_number(coordinate[1], "Route geometry contains an invalid latitude.")
        if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
            raise CheckpointGenerationError("Route geometry coordinates are outside valid ranges.")
        coordinates.append((longitude, latitude))
    return coordinates


def _finite_number(value: Any, message: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise CheckpointGenerationError(message) from exc
    if not math.isfinite(number):
        raise CheckpointGenerationError(message)
    return number


def _positive_finite(value: Any, message: str) -> float:
    number = _finite_number(value, message)
    if number <= 0:
        raise CheckpointGenerationError(message)
    return number


def _haversine_distance_meters(first: tuple[float, float], second: tuple[float, float]) -> float:
    first_lon, first_lat = map(math.radians, first)
    second_lon, second_lat = map(math.radians, second)
    delta_latitude = second_lat - first_lat
    delta_longitude = second_lon - first_lon
    haversine = (
        math.sin(delta_latitude / 2) ** 2
        + math.cos(first_lat) * math.cos(second_lat) * math.sin(delta_longitude / 2) ** 2
    )
    central_angle = 2 * math.atan2(math.sqrt(haversine), math.sqrt(max(0.0, 1.0 - haversine)))
    return EARTH_RADIUS_METERS * central_angle


def _interpolate_at_distance(
    coordinates: list[tuple[float, float]],
    cumulative_distances: list[float],
    distance_meters: float,
) -> tuple[float, float]:
    if distance_meters <= 0:
        return coordinates[0]
    if distance_meters >= cumulative_distances[-1]:
        return coordinates[-1]

    segment_index = min(bisect_right(cumulative_distances, distance_meters) - 1, len(coordinates) - 2)
    segment_start = cumulative_distances[segment_index]
    segment_length = cumulative_distances[segment_index + 1] - segment_start
    if segment_length <= 0:
        return coordinates[segment_index + 1]
    fraction = (distance_meters - segment_start) / segment_length
    return _spherical_interpolate(coordinates[segment_index], coordinates[segment_index + 1], fraction)


def _spherical_interpolate(
    first: tuple[float, float], second: tuple[float, float], fraction: float
) -> tuple[float, float]:
    if fraction <= 0:
        return first
    if fraction >= 1:
        return second
    first_vector = _unit_vector(first)
    second_vector = _unit_vector(second)
    dot = min(1.0, max(-1.0, sum(a * b for a, b in zip(first_vector, second_vector))))
    angle = math.acos(dot)
    if angle < 1e-12:
        return first
    sin_angle = math.sin(angle)
    if abs(sin_angle) < 1e-12:
        # Nearly antipodal adjacent route vertices are malformed for practical routing;
        # still interpolate across the shorter longitude direction deterministically.
        longitude_delta = (second[0] - first[0] + 180) % 360 - 180
        return ((first[0] + longitude_delta * fraction + 180) % 360 - 180,
                first[1] + (second[1] - first[1]) * fraction)
    weight_first = math.sin((1 - fraction) * angle) / sin_angle
    weight_second = math.sin(fraction * angle) / sin_angle
    x = weight_first * first_vector[0] + weight_second * second_vector[0]
    y = weight_first * first_vector[1] + weight_second * second_vector[1]
    z = weight_first * first_vector[2] + weight_second * second_vector[2]
    longitude = math.degrees(math.atan2(y, x))
    latitude = math.degrees(math.atan2(z, math.hypot(x, y)))
    return longitude, latitude


def _unit_vector(coordinate: tuple[float, float]) -> tuple[float, float, float]:
    longitude, latitude = map(math.radians, coordinate)
    cos_latitude = math.cos(latitude)
    return (
        cos_latitude * math.cos(longitude),
        cos_latitude * math.sin(longitude),
        math.sin(latitude),
    )
