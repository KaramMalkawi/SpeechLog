from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import models

from core.tenancy import get_tenant_context

if TYPE_CHECKING:
    from django.db.models.query import QuerySet


class TenantAwareQuerySet(models.QuerySet):
    def _apply_tenant_filter(self) -> QuerySet:
        ctx = get_tenant_context()
        if ctx is None:
            return self
        return self.filter(community_id=ctx.community_id, city_id=ctx.city_id)


class TenantAwareManager(models.Manager.from_queryset(TenantAwareQuerySet)):  # type: ignore[misc]
    def get_queryset(self) -> QuerySet:
        return super().get_queryset()._apply_tenant_filter()


class CityScopedQuerySet(models.QuerySet):
    def _apply_city_filter(self) -> QuerySet:
        ctx = get_tenant_context()
        if ctx is None:
            return self
        return self.filter(city_id=ctx.city_id)


class CityScopedManager(models.Manager.from_queryset(CityScopedQuerySet)):  # type: ignore[misc]
    def get_queryset(self) -> QuerySet:
        return super().get_queryset()._apply_city_filter()
