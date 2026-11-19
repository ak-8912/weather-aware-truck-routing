import logging
import os
from typing import Any
from urllib.parse import urljoin

import requests
from django.conf import settings

from apps.routing.services.route_processor import normalize_route_response
from apps.routing.services.routing_provider import (
    InvalidProviderResponse,
    ProviderAuthenticationError,
    ProviderConfigurationError,
    ProviderRateLimitError,
    ProviderRequestError,
    ProviderTimeoutError,
    RoutingProvider,
    NoRoutesFound,
)

logger = logging.getLogger(__name__)


class OpenRouteServiceProvider(RoutingProvider):
    PROFILE = "driving-hgv"
    ALTERNATIVE_ROUTES = {"target_count": 3, "share_factor": 0.6, "weight_factor": 1.4}

    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self.base_url = getattr(settings, "OPENROUTESERVICE_BASE_URL", "https://api.heigit.org/openrouteservice").rstrip("/")
        self.geocoding_base_url = getattr(settings, "OPENROUTESERVICE_GEOCODING_BASE_URL", "https://api.heigit.org/pelias/v1").rstrip("/")
        self.api_key = os.getenv("OPENROUTESERVICE_API_KEY", "").strip()
        self.timeout = getattr(settings, "OPENROUTESERVICE_TIMEOUT", 15)

    def get_routes(self, origin: dict[str, Any], destination: dict[str, Any]) -> list[dict[str, Any]]:
        payload = {
            "coordinates": [
                [origin["longitude"], origin["latitude"]],
                [destination["longitude"], destination["latitude"]],
            ],
            "units": "m",
            "instructions": False,
            # ORS may return fewer routes than target_count; the processor caps results at three.
            "alternative_routes": self.ALTERNATIVE_ROUTES.copy(),
        }
        response = self._request_json(
            "POST",
            f"/v2/directions/{self.PROFILE}/geojson",
            json=payload,
            accept="application/geo+json",
        )
        return normalize_route_response(response)

    def geocode(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        response = self._request_json(
            "GET",
            "/search",
            params={"text": query, "size": limit},
            base_url=self.geocoding_base_url,
        )
        return normalize_geocoding_response(response, limit=limit)

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        accept: str = "application/json",
        base_url: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if not self.api_key or self.api_key.lower() == "replace_me":
            raise ProviderConfigurationError()

        url = urljoin(f"{(base_url or self.base_url)}/", path.lstrip("/"))
        headers = {"Authorization": self.api_key, "Accept": accept}
        if method == "POST":
            headers["Content-Type"] = "application/json"
        try:
            response = self.session.request(method, url, headers=headers, timeout=self.timeout, **kwargs)
        except requests.Timeout as exc:
            logger.warning("OpenRouteService request timed out", extra={"event": "ors_timeout", "path": path})
            raise ProviderTimeoutError() from exc
        except requests.RequestException as exc:
            logger.warning("OpenRouteService request failed", extra={"event": "ors_request_failed", "path": path})
            raise ProviderRequestError() from exc

        request_json = kwargs.get("json")
        if (
            response.status_code == 400
            and isinstance(request_json, dict)
            and "alternative_routes" in request_json
            and _is_alternative_distance_restriction(response)
        ):
            logger.info("OpenRouteService alternative route distance limit reached; retrying without alternatives", extra={"event": "ors_alternatives_limit"})
            primary_route_payload = request_json.copy()
            primary_route_payload.pop("alternative_routes", None)
            return self._request_json(method, path, accept=accept, base_url=base_url, **{**kwargs, "json": primary_route_payload})

        if response.status_code in (400, 404) and _is_no_route_response(response):
            raise NoRoutesFound()

        if response.status_code == 429:
            raise ProviderRateLimitError()
        if response.status_code in (401, 403):
            logger.error("OpenRouteService rejected credentials", extra={"event": "ors_auth_failed", "status": response.status_code})
            raise ProviderAuthenticationError()
        if not 200 <= response.status_code < 300:
            logger.warning("OpenRouteService returned an error", extra={"event": "ors_http_error", "status": response.status_code, "path": path})
            raise ProviderRequestError()
        try:
            payload = response.json()
        except (ValueError, requests.JSONDecodeError) as exc:
            raise InvalidProviderResponse() from exc
        if not isinstance(payload, dict):
            raise InvalidProviderResponse()
        return payload


def _is_alternative_distance_restriction(response: requests.Response) -> bool:
    message = _provider_error_message(response).casefold()
    return "alternative" in message and any(term in message for term in ("distance", "100000", "100 km", "maximum"))


def _is_no_route_response(response: requests.Response) -> bool:
    message = _provider_error_message(response).casefold()
    return any(term in message for term in ("no route found", "could not find a route", "route not found", "no routable point"))


def _provider_error_message(response: requests.Response) -> str:
    try:
        payload = response.json()
    except (ValueError, requests.JSONDecodeError):
        return ""
    if not isinstance(payload, dict):
        return ""
    error = payload.get("error")
    if isinstance(error, dict):
        return str(error.get("message", ""))
    return str(payload.get("message", ""))


def normalize_geocoding_response(payload: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
    features = payload.get("features")
    if not isinstance(features, list):
        raise InvalidProviderResponse()

    locations = []
    for feature in features:
        if not isinstance(feature, dict):
            continue
        geometry = feature.get("geometry")
        properties = feature.get("properties")
        if not isinstance(geometry, dict) or not isinstance(properties, dict):
            continue
        coordinates = geometry.get("coordinates")
        if not isinstance(coordinates, (list, tuple)) or len(coordinates) < 2:
            continue
        try:
            longitude, latitude = float(coordinates[0]), float(coordinates[1])
        except (TypeError, ValueError):
            continue
        if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
            continue
        name = properties.get("label") or properties.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        address = {
            key: properties[key]
            for key in ("locality", "region", "country", "country_a")
            if isinstance(properties.get(key), str) and properties[key].strip()
        }
        locations.append({"name": name.strip(), "latitude": latitude, "longitude": longitude, "address": address})
        if len(locations) == limit:
            break
    return locations
