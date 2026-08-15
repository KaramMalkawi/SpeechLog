from __future__ import annotations

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.founders.models import Founder, FounderApplication


class CityFounderSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    user_id = serializers.UUIDField()
    full_name = serializers.CharField()
    email = serializers.EmailField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    city_id = serializers.UUIDField()
    city_name = serializers.CharField(allow_blank=True)
    country_id = serializers.UUIDField(allow_null=True)
    country_name = serializers.CharField(allow_blank=True)
    country_code = serializers.CharField(allow_blank=True)


class CityFounderCreateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=160)
    email = serializers.EmailField()
    city_id = serializers.UUIDField()


class CityFounderUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=160, required=False)
    email = serializers.EmailField(required=False)
    city_id = serializers.UUIDField(required=False)
    status = serializers.ChoiceField(choices=Founder.Status.choices, required=False)


class CityFounderDeleteSerializer(serializers.Serializer):
    confirmation_name = serializers.CharField(max_length=160)


class FounderDashboardOverviewSerializer(serializers.Serializer):
    full_name = serializers.CharField()
    email = serializers.EmailField()
    status = serializers.CharField()
    city_id = serializers.UUIDField()
    city_name = serializers.CharField(allow_blank=True)
    country_name = serializers.CharField(allow_blank=True)
    welcome_message = serializers.CharField()


class FounderChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)

    def validate_new_password(self, value: str) -> str:
        validate_password(value)
        return value


class FounderApplicationSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    sheet_row = serializers.IntegerField()
    submitted_at = serializers.DateTimeField(allow_null=True)
    email = serializers.EmailField(allow_blank=True)
    country_name = serializers.CharField(allow_blank=True)
    full_name = serializers.CharField(allow_blank=True)
    status = serializers.CharField()
    answers = serializers.DictField(child=serializers.CharField(allow_blank=True))
    sheet_url = serializers.CharField(allow_blank=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class FounderApplicationStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=FounderApplication.Status.choices)


class FounderApplicationSyncStateSerializer(serializers.Serializer):
    last_synced_at = serializers.DateTimeField(allow_null=True)
    last_sync_error = serializers.CharField(allow_blank=True)
    last_sync_row_count = serializers.IntegerField()
    spreadsheet_id = serializers.CharField(allow_blank=True)
    spreadsheet_url = serializers.CharField(allow_blank=True)


class FounderApplicationSyncResultSerializer(serializers.Serializer):
    created = serializers.IntegerField()
    updated = serializers.IntegerField()
    total = serializers.IntegerField()
    last_synced_at = serializers.DateTimeField(allow_null=True)
    spreadsheet_url = serializers.CharField(allow_blank=True)
