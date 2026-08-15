from __future__ import annotations

from rest_framework import serializers

from apps.adminpanel.models import AdminAuditLog


class AdminAuditLogSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    action = serializers.CharField()
    action_label = serializers.CharField()
    actor_id = serializers.UUIDField()
    actor_email = serializers.EmailField()
    actor_full_name = serializers.CharField(allow_blank=True)
    actor_role = serializers.CharField()
    actor_role_label = serializers.CharField()
    summary = serializers.CharField()
    metadata = serializers.DictField()


class AdminAuditLogActionOptionSerializer(serializers.Serializer):
    value = serializers.CharField()
    label = serializers.CharField()


def audit_action_options() -> list[dict[str, str]]:
    return [
        {"value": value, "label": label}
        for value, label in AdminAuditLog.Action.choices
    ]
