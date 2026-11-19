from abc import ABC, abstractmethod
from typing import Any

from rest_framework.exceptions import APIException


class RoutingProviderError(APIException):
    status_code = 502
    default_code = "routing_provider_error"
    default_detail = "The routing provider could not complete the request."


class ProviderConfigurationError(RoutingProviderError):
    status_code = 503
    default_code = "routing_provider_not_configured"
    default_detail = "Routing is not configured. Add an OpenRouteService API key to the backend environment."


class ProviderTimeoutError(RoutingProviderError):
    status_code = 504
    default_code = "routing_provider_timeout"
    default_detail = "The routing provider timed out. Please try again."


class ProviderRateLimitError(RoutingProviderError):
    status_code = 503
    default_code = "routing_provider_rate_limited"
    default_detail = "The routing provider is rate limited. Please try again later."


class ProviderAuthenticationError(RoutingProviderError):
    status_code = 502
    default_code = "routing_provider_authentication_failed"
    default_detail = "The routing provider rejected its configured credentials."


class ProviderRequestError(RoutingProviderError):
    status_code = 502
    default_code = "routing_provider_unavailable"
    default_detail = "The routing provider is temporarily unavailable."


class NoRoutesFound(APIException):
    status_code = 422
    default_code = "no_routes_found"
    default_detail = "The routing provider did not return a route for these locations."


class InvalidProviderResponse(RoutingProviderError):
    default_code = "invalid_routing_provider_response"
    default_detail = "The routing provider returned an invalid response."


class RoutingProvider(ABC):
    @abstractmethod
    def get_routes(self, origin: dict[str, Any], destination: dict[str, Any]) -> list[dict[str, Any]]:
        """Return normalized route alternatives from the configured provider."""

    @abstractmethod
    def geocode(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Return normalized location suggestions from the configured provider."""
