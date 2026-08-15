from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from apps.tenancy.models import Community

_tenant_context: ContextVar[TenantContext | None] = ContextVar("tenant_context", default=None)


@dataclass(frozen=True, slots=True)
class TenantContext:
    community_id: UUID
    city_id: UUID

    @classmethod
    def from_community(cls, community: Community) -> TenantContext:
        return cls(community_id=community.id, city_id=community.city_id)


def get_tenant_context() -> TenantContext | None:
    return _tenant_context.get()


def set_tenant_context(context: TenantContext | None) -> None:
    _tenant_context.set(context)


def clear_tenant_context() -> None:
    _tenant_context.set(None)
