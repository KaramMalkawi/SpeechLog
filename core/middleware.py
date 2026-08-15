from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from django.http import HttpRequest, HttpResponse

from core.tenancy import TenantContext, clear_tenant_context, set_tenant_context

if TYPE_CHECKING:
    from apps.tenancy.models import Community

COMMUNITY_HEADER = "HTTP_X_COMMUNITY_ID"


class TenantMiddleware:
    """Resolve the active community and set row-level tenant context for the request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        community = self._resolve_community(request)
        if community is not None:
            set_tenant_context(TenantContext.from_community(community))
            request.community = community  # type: ignore[attr-defined]
        else:
            request.community = None  # type: ignore[attr-defined]

        try:
            return self.get_response(request)
        finally:
            clear_tenant_context()

    def _resolve_community(self, request: HttpRequest) -> Community | None:
        from apps.tenancy.models import Community

        community_id = self._extract_community_id(request)
        if community_id is None:
            return None

        try:
            return Community.objects.select_related("city").get(
                id=community_id,
                is_active=True,
            )
        except Community.DoesNotExist:
            return None

    def _extract_community_id(self, request: HttpRequest) -> UUID | None:
        header_value = request.META.get(COMMUNITY_HEADER)
        if header_value:
            try:
                return UUID(header_value)
            except ValueError:
                return None

        user = getattr(request, "user", None)
        if user is not None and getattr(user, "is_authenticated", False):
            active_community_id = getattr(user, "active_community_id", None)
            if active_community_id:
                return active_community_id

        return None
