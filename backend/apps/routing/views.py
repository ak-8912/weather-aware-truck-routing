import hashlib
import json
import logging

from django.core.cache import cache
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.routing.serializers import (
    GeocodingQuerySerializer,
    LocationSuggestionSerializer,
    RouteAlternativesRequestSerializer,
    RouteAlternativesResponseSerializer,
)
from apps.routing.services.openrouteservice import OpenRouteServiceProvider

logger = logging.getLogger(__name__)


def get_routing_provider():
    return OpenRouteServiceProvider()


class RouteAlternativesView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        request_serializer = RouteAlternativesRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        validated = request_serializer.validated_data
        routes = get_routing_provider().get_routes(validated["origin"], validated["destination"])
        notice = None
        if len(routes) < 3:
            notice = f"OpenRouteService returned {len(routes)} route(s); fewer than the requested maximum of 3."
        response_serializer = RouteAlternativesResponseSerializer(data={
            "routes": routes,
            "route_count": len(routes),
            "alternatives_notice": notice,
            "provider": "OpenRouteService",
        })
        response_serializer.is_valid(raise_exception=True)
        logger.info("Route alternatives retrieved", extra={"event": "routes_retrieved", "route_count": len(routes)})
        return Response(response_serializer.data)


class GeocodingSearchView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        query_serializer = GeocodingQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        query = query_serializer.validated_data["q"]
        limit = query_serializer.validated_data["limit"]
        cache_identity = hashlib.sha256(f"{query.casefold()}:{limit}".encode()).hexdigest()
        cache_key = f"geocoding:v1:{cache_identity}"
        suggestions = cache.get(cache_key)
        if suggestions is None:
            suggestions = get_routing_provider().geocode(query, limit)
            cache.set(cache_key, suggestions, timeout=3600)
        serializer = LocationSuggestionSerializer(data=suggestions, many=True)
        serializer.is_valid(raise_exception=True)
        return Response({"results": serializer.data})
