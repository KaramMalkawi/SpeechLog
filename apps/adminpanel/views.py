from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.authentication import VerifiedJWTAuthentication
from apps.accounts.permissions import IsPlatformAdmin
from apps.adminpanel.selectors import list_admin_audit_logs
from apps.adminpanel.serializers import (
    AdminAuditLogSerializer,
    audit_action_options,
)
from apps.adminpanel.services import audit_log_to_payload


class AdminAuditLogListView(APIView):
    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsPlatformAdmin]

    @extend_schema(
        tags=["adminpanel"],
        summary="List admin audit logs",
        parameters=[
            OpenApiParameter(
                name="actor_role",
                required=False,
                type=str,
                description="Filter by actor role: admin | superadmin",
            ),
            OpenApiParameter(name="action", required=False, type=str),
            OpenApiParameter(name="search", required=False, type=str),
            OpenApiParameter(name="limit", required=False, type=int),
        ],
        responses={200: AdminAuditLogSerializer(many=True)},
    )
    def get(self, request):
        logs = list_admin_audit_logs(
            actor_role=request.query_params.get("actor_role") or None,
            action=request.query_params.get("action") or None,
            search=request.query_params.get("search") or None,
            limit=request.query_params.get("limit") or 200,
        )
        payload = [audit_log_to_payload(log) for log in logs]
        return Response(
            {
                "results": AdminAuditLogSerializer(payload, many=True).data,
                "actions": audit_action_options(),
            }
        )
