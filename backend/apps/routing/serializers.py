from rest_framework import serializers


class LocationCoordinatesSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)


class RouteAlternativesRequestSerializer(serializers.Serializer):
    origin = LocationCoordinatesSerializer()
    destination = LocationCoordinatesSerializer()

    def validate(self, attrs):
        origin = attrs["origin"]
        destination = attrs["destination"]
        if (origin["latitude"], origin["longitude"]) == (destination["latitude"], destination["longitude"]):
            raise serializers.ValidationError("Origin and destination must be different coordinates.")
        return attrs


class RouteSerializer(serializers.Serializer):
    route_id = serializers.CharField()
    geometry = serializers.ListField(child=serializers.ListField(child=serializers.FloatField(), min_length=2, max_length=2), min_length=2)
    distance_meters = serializers.FloatField(min_value=0)
    duration_seconds = serializers.FloatField(min_value=0)


class RouteAlternativesResponseSerializer(serializers.Serializer):
    routes = RouteSerializer(many=True)
    route_count = serializers.IntegerField(min_value=1, max_value=3)
    alternatives_notice = serializers.CharField(required=False, allow_null=True)
    provider = serializers.CharField()


class GeocodingQuerySerializer(serializers.Serializer):
    q = serializers.CharField(min_length=2, max_length=160, trim_whitespace=True)
    limit = serializers.IntegerField(min_value=1, max_value=5, default=5)


class LocationSuggestionSerializer(serializers.Serializer):
    name = serializers.CharField()
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)
    address = serializers.DictField(child=serializers.CharField(), allow_empty=True)
