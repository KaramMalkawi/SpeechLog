from __future__ import annotations

from typing import Any
from uuid import UUID

from django.db import transaction

from apps.guidebook.exceptions import PartnerNotFound, PartnerValidationError
from apps.guidebook.models import Partner, PartnerScope
from apps.tenancy.models import Community
from apps.tenancy.selectors import get_community_by_id


def _assert_scope_fields(*, scope: str, community_id: UUID | None, city_id: UUID) -> None:
    if scope == PartnerScope.CITY_WIDE:
        if community_id is not None:
            raise PartnerValidationError("city_wide partners must not set community_id.")
        return
    if scope == PartnerScope.COMMUNITY:
        if community_id is None:
            raise PartnerValidationError("community partners require community_id.")
        community = get_community_by_id(community_id)
        if community is None:
            raise PartnerValidationError("Community not found.")
        if community.city_id != city_id:
            raise PartnerValidationError("community_id must belong to the partner city.")
        return
    raise PartnerValidationError("Invalid partner scope.")


@transaction.atomic
def create_partner(
    *,
    city_id: UUID,
    name: str,
    scope: str = PartnerScope.CITY_WIDE,
    community_id: UUID | None = None,
    **fields: Any,
) -> Partner:
    _assert_scope_fields(scope=scope, community_id=community_id, city_id=city_id)
    return Partner.all_objects.create(
        city_id=city_id,
        scope=scope,
        community_id=community_id,
        name=name,
        **fields,
    )


@transaction.atomic
def update_partner(*, partner_id: UUID, **fields: Any) -> Partner:
    partner = Partner.all_objects.select_for_update().filter(pk=partner_id).first()
    if partner is None:
        raise PartnerNotFound("Partner not found.")

    scope = fields.get("scope", partner.scope)
    community_id = fields.get("community_id", partner.community_id)
    city_id = fields.get("city_id", partner.city_id)
    _assert_scope_fields(scope=scope, community_id=community_id, city_id=city_id)

    for key, value in fields.items():
        if hasattr(partner, key):
            setattr(partner, key, value)
    partner.save()
    return partner


@transaction.atomic
def upsert_partner_by_name(
    *,
    city_id: UUID,
    name: str,
    scope: str = PartnerScope.CITY_WIDE,
    community_id: UUID | None = None,
    **fields: Any,
) -> Partner:
    """Seed helper: update existing active partner with the same name in the city."""
    existing = (
        Partner.all_objects.filter(
            city_id=city_id,
            name=name,
            is_active=True,
            scope=scope,
            community_id=community_id,
        )
        .order_by("created_at")
        .first()
    )
    if existing is not None:
        return update_partner(partner_id=existing.id, **fields)
    return create_partner(
        city_id=city_id,
        name=name,
        scope=scope,
        community_id=community_id,
        **fields,
    )


def community_city_id(community: Community) -> UUID:
    return community.city_id
