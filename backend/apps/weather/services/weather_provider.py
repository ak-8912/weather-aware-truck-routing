from abc import ABC, abstractmethod
from typing import Any

from rest_framework.exceptions import APIException


class WeatherProviderError(APIException):
    status_code = 502
    default_code = "weather_provider_error"
    default_detail = "The weather provider could not complete the request."


class WeatherProviderTimeout(WeatherProviderError):
    status_code = 504
    default_code = "weather_provider_timeout"
    default_detail = "The weather forecast provider timed out. Please try again."


class WeatherProviderRateLimited(WeatherProviderError):
    status_code = 503
    default_code = "weather_provider_rate_limited"
    default_detail = "The weather forecast provider is rate limited. Please try again later."


class WeatherProviderUnavailable(WeatherProviderError):
    status_code = 502
    default_code = "weather_provider_unavailable"
    default_detail = "The weather forecast provider is temporarily unavailable."


class InvalidWeatherResponse(WeatherProviderError):
    default_code = "invalid_weather_provider_response"
    default_detail = "The weather forecast provider returned an invalid response."


class WeatherProvider(ABC):
    @abstractmethod
    def fetch_hourly_forecasts(self, locations: list[dict[str, float]]) -> list[list[dict[str, Any]]]:
        """Return normalized hourly forecast rows for each location, in input order."""
