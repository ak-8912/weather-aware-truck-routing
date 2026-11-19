import logging
import os
from datetime import timezone

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.trips.serializers import HealthResponseSerializer, TripAnalysisRequestSerializer, TripAnalysisResponseSerializer

logger = logging.getLogger(__name__)


class HealthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        payload = {
            "status": "ok",
            "version": os.getenv("APP_VERSION", "0.1.0"),
            "providers": {
                "routing_configured": bool(os.getenv("OPENROUTESERVICE_API_KEY")),
                "weather_provider": "public",
            },
        }
        serializer = HealthResponseSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        logger.info("Health check completed", extra={"event": "health_check"})
        return Response(serializer.data)


class TripAnalysisView(APIView):
    """Compose routing, checkpoint, weather, and risk services for a trip."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        from apps.risk_engine.services.risk_miles import calculate_route_risk
        from apps.risk_engine.services.route_recommender import recommend_route
        from apps.routing.services.checkpoint_generator import generate_weather_checkpoints
        from apps.routing.views import get_routing_provider
        from apps.weather.services.checkpoint_weather import enrich_checkpoints_with_weather
        from apps.weather.services.open_meteo import OpenMeteoProvider

        request_serializer = TripAnalysisRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        trip = request_serializer.validated_data
        departure = trip["departure_datetime"]
        if departure.utcoffset() is None:
            departure = departure.replace(tzinfo=timezone.utc)

        routes = get_routing_provider().get_routes(trip["origin"], trip["destination"])
        weather_provider = OpenMeteoProvider()
        analyzed_routes = []
        for route in routes:
            checkpoints = generate_weather_checkpoints(route, departure, int(trip["sampling_interval"]))
            enriched = enrich_checkpoints_with_weather(checkpoints, weather_provider)
            risk = calculate_route_risk(route, enriched, trip["load_weight"])
            analyzed_routes.append({**route, **risk})

        recommendation = recommend_route(analyzed_routes)
        minimum_coverage = min(route["weather_coverage_percent"] for route in analyzed_routes)
        payload = {
            "trip": {
                "origin": trip["origin"],
                "destination": trip["destination"],
                "departure_datetime": departure,
                "load_weight": trip["load_weight"],
            },
            "routes": analyzed_routes,
            **recommendation,
            "analysis_metadata": {
                "routing_provider": "OpenRouteService",
                "weather_provider": "Open-Meteo",
                "sampling_interval": int(trip["sampling_interval"]),
                "weather_coverage": round(minimum_coverage, 4),
                "route_count": len(analyzed_routes),
            },
        }
        response_serializer = TripAnalysisResponseSerializer(data=payload)
        response_serializer.is_valid(raise_exception=True)
        logger.info("Trip analysis completed", extra={
            "event": "trip_analysis_completed",
            "route_count": len(analyzed_routes),
            "sampling_interval": int(trip["sampling_interval"]),
        })
        return Response(response_serializer.data)
