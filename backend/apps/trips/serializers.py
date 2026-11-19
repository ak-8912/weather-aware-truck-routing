from rest_framework import serializers


class ProviderStatusSerializer(serializers.Serializer):
    routing_configured = serializers.BooleanField()
    weather_provider = serializers.ChoiceField(choices=("public",))


class HealthResponseSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=("ok",))
    version = serializers.CharField()
    providers = ProviderStatusSerializer()
