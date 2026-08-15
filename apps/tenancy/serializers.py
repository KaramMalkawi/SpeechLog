from __future__ import annotations

from rest_framework import serializers

from apps.gatherings.models import GATHERING_SYSTEM_MAX_ATTENDEES


class CountryCatalogSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()
    slug = serializers.CharField()


class PlatformSettingsSerializer(serializers.Serializer):
    gathering_hard_cap = serializers.IntegerField()
    gathering_member_min_events = serializers.IntegerField()
    gathering_non_member_min_events = serializers.IntegerField()
    event_expat_capacity_percent = serializers.IntegerField()
    updated_at = serializers.DateTimeField()


class PlatformSettingsUpdateSerializer(serializers.Serializer):
    gathering_hard_cap = serializers.IntegerField(
        min_value=2,
        max_value=GATHERING_SYSTEM_MAX_ATTENDEES,
        required=False,
    )
    gathering_member_min_events = serializers.IntegerField(min_value=0, required=False)
    gathering_non_member_min_events = serializers.IntegerField(min_value=0, required=False)
    event_expat_capacity_percent = serializers.IntegerField(
        min_value=0,
        max_value=100,
        required=False,
    )


class OperationalCountrySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    code = serializers.CharField()
    slug = serializers.CharField()
    currency = serializers.CharField()
    allows_residence = serializers.BooleanField()
    is_active = serializers.BooleanField()
    city_count = serializers.IntegerField()


class OperationalCountryCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    code = serializers.CharField(max_length=2, required=False, allow_blank=True)
    currency = serializers.CharField(max_length=3, default="JOD", required=False)
    allows_residence = serializers.BooleanField(default=True, required=False)
    is_active = serializers.BooleanField(default=True, required=False)


class OperationalCountryUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120, required=False)
    code = serializers.CharField(max_length=2, required=False)
    currency = serializers.CharField(max_length=3, required=False)
    allows_residence = serializers.BooleanField(required=False)
    is_active = serializers.BooleanField(required=False)


class OperationalCitySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.CharField()
    is_active = serializers.BooleanField()
    country_id = serializers.UUIDField()
    country_name = serializers.CharField()
    country_code = serializers.CharField()
    country_currency = serializers.CharField()


class OperationalCityCreateSerializer(serializers.Serializer):
    country_id = serializers.UUIDField()
    name = serializers.CharField(max_length=120)
    is_active = serializers.BooleanField(default=True, required=False)


class OperationalCityUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120, required=False)
    is_active = serializers.BooleanField(required=False)
