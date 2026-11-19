from rest_framework import serializers
from apps.routing.services.checkpoint_generator import SUPPORTED_INTERVALS_MILES


class ProviderStatusSerializer(serializers.Serializer):
    routing_configured = serializers.BooleanField()
    weather_provider = serializers.ChoiceField(choices=("public",))


class HealthResponseSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=("ok",))
    version = serializers.CharField()
    providers = ProviderStatusSerializer()


class TripLocationSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)


class TripAnalysisRequestSerializer(serializers.Serializer):
    origin = TripLocationSerializer()
    destination = TripLocationSerializer()
    departure_datetime = serializers.DateTimeField()
    load_weight = serializers.FloatField(min_value=0, max_value=200000)
    sampling_interval = serializers.ChoiceField(choices=sorted(SUPPORTED_INTERVALS_MILES))

    def validate(self, attrs):
        origin, destination = attrs["origin"], attrs["destination"]
        if (origin["latitude"], origin["longitude"]) == (destination["latitude"], destination["longitude"]):
            raise serializers.ValidationError({"destination": "Origin and destination must be different coordinates."})
        if attrs["departure_datetime"].utcoffset() is None:
            raise serializers.ValidationError({"departure_datetime": "Departure time must include a timezone."})
        return attrs


class AnalyzedRouteSerializer(serializers.Serializer):
    route_id = serializers.CharField()
    geometry = serializers.ListField(child=serializers.ListField(child=serializers.FloatField(), min_length=2, max_length=2), min_length=2)
    distance_meters = serializers.FloatField(min_value=0)
    distance_miles = serializers.FloatField(min_value=0)
    duration_seconds = serializers.FloatField(min_value=0)
    total_checkpoints = serializers.IntegerField(min_value=2)
    risk_miles = serializers.DictField(child=serializers.FloatField(min_value=0))
    unavailable_weather_miles = serializers.FloatField(min_value=0)
    known_no_travel_exposure_miles = serializers.FloatField(min_value=0)
    no_travel_exposure_miles = serializers.FloatField(min_value=0)
    average_risk_score = serializers.FloatField(min_value=1, max_value=5, allow_null=True)
    maximum_risk_level = serializers.CharField(allow_null=True)
    weather_coverage_percent = serializers.FloatField(min_value=0, max_value=100)
    has_no_travel_exposure = serializers.BooleanField()
    unsafe = serializers.BooleanField()
    safe_to_travel = serializers.BooleanField()
    estimated_arrival_time = serializers.DateTimeField()
    checkpoints = serializers.ListField(child=serializers.DictField())


class TripAnalysisResponseSerializer(serializers.Serializer):
    trip = serializers.DictField()
    routes = AnalyzedRouteSerializer(many=True)
    recommended_route_id = serializers.CharField()
    recommendation_explanation = serializers.DictField()
    analysis_metadata = serializers.DictField()
