import hashlib
import json
import math
from typing import Any

from apps.routing.services.routing_provider import InvalidProviderResponse, NoRoutesFound


def normalize_route_response(payload: dict[str, Any], limit: int = 3) -> list[dict[str, Any]]:
    features = payload.get("features")
    if not isinstance(features, list):
        raise InvalidProviderResponse()
    if not features:
        raise NoRoutesFound()

    routes = []
    seen_geometries = set()
    for feature in features:
        if len(routes) >= limit:
            break
        route = _normalize_feature(feature)
        fingerprint = hashlib.sha256(json.dumps(route["geometry"], separators=(",", ":")).encode()).hexdigest()
        if fingerprint in seen_geometries:
            continue
        seen_geometries.add(fingerprint)
        route["route_id"] = f"route-{len(routes) + 1}"
        routes.append(route)

    if not routes:
        raise NoRoutesFound()
    return routes


def _normalize_feature(feature: Any) -> dict[str, Any]:
    if not isinstance(feature, dict):
        raise InvalidProviderResponse()
    geometry = feature.get("geometry")
    properties = feature.get("properties")
    if not isinstance(geometry, dict) or geometry.get("type") != "LineString":
        raise InvalidProviderResponse()
    if not isinstance(properties, dict):
        raise InvalidProviderResponse()
    summary = properties.get("summary")
    coordinates = geometry.get("coordinates")
    if not isinstance(summary, dict) or not isinstance(coordinates, list) or len(coordinates) < 2:
        raise InvalidProviderResponse()
    distance = _positive_finite_number(summary.get("distance"))
    duration = _positive_finite_number(summary.get("duration"))
    normalized_coordinates = []
    for coordinate in coordinates:
        if not isinstance(coordinate, (list, tuple)) or len(coordinate) < 2:
            raise InvalidProviderResponse()
        longitude = _finite_number(coordinate[0])
        latitude = _finite_number(coordinate[1])
        if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
            raise InvalidProviderResponse()
        normalized_coordinates.append([longitude, latitude])
    return {
        "geometry": normalized_coordinates,
        "distance_meters": distance,
        "duration_seconds": duration,
    }


def _finite_number(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise InvalidProviderResponse() from exc
    if not math.isfinite(number):
        raise InvalidProviderResponse()
    return number


def _positive_finite_number(value: Any) -> float:
    number = _finite_number(value)
    if number <= 0:
        raise InvalidProviderResponse()
    return number
