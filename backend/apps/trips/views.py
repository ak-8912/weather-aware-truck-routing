import logging
import os

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.trips.serializers import HealthResponseSerializer

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
