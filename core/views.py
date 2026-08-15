from __future__ import annotations

from django.core.cache import cache
from django.db import connection
from django.db.utils import OperationalError
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.serializers import HealthCheckSerializer


@extend_schema(
    tags=["system"],
    summary="Health check",
    description="Reports database and Redis connectivity.",
    responses={
        status.HTTP_200_OK: HealthCheckSerializer,
        status.HTTP_503_SERVICE_UNAVAILABLE: HealthCheckSerializer,
    },
)
class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        checks = {
            "database": self._check_database(),
            "redis": self._check_redis(),
        }
        healthy = all(checks.values())
        return Response(
            {"status": "ok" if healthy else "degraded", "checks": checks},
            status=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    @staticmethod
    def _check_database() -> bool:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return True
        except OperationalError:
            return False

    @staticmethod
    def _check_redis() -> bool:
        try:
            cache.set("health_check", "ok", timeout=5)
            return cache.get("health_check") == "ok"
        except Exception:
            return False
