from rest_framework import serializers


class HealthCheckSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["ok", "degraded"])
    checks = serializers.DictField(child=serializers.BooleanField())
