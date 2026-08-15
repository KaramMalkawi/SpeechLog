from __future__ import annotations

from uuid import UUID

from django.db.models import Q, QuerySet

from apps.accounts.models import User
from apps.guidebook.models import Partner, PartnerCategory, PartnerScope
from apps.tenancy.selectors import get_city_by_id, get_community_by_id
from core.storage import build_media_url


def list_partners(
    *,
    city_id: UUID,
    community_id: UUID | None = None,
    category: str | None = None,
    include_inactive: bool = False,
) -> QuerySet[Partner]:
    """
    City-shared guidebook listings.

    Always includes city_wide partners for the city. When community_id is set,
    also includes that community's isolated partners.
    """
    qs = Partner.all_objects.filter(city_id=city_id)
    if not include_inactive:
        qs = qs.filter(is_active=True)

    if community_id is not None:
        qs = qs.filter(
            Q(scope=PartnerScope.CITY_WIDE)
            | Q(scope=PartnerScope.COMMUNITY, community_id=community_id)
        )
    else:
        qs = qs.filter(scope=PartnerScope.CITY_WIDE)

    if category:
        normalized = category.strip().lower()
        if normalized and normalized != "all":
            # Accept API slug or display label ("Restaurant").
            choices = {c.value: c.value for c in PartnerCategory}
            label_to_value = {c.label.lower(): c.value for c in PartnerCategory}
            resolved = choices.get(normalized) or label_to_value.get(normalized)
            if resolved:
                qs = qs.filter(category=resolved)

    return qs.order_by("sort_order", "name", "id")


def get_partner_for_city(*, partner_id: UUID, city_id: UUID) -> Partner | None:
    return Partner.all_objects.filter(pk=partner_id, city_id=city_id, is_active=True).first()


def get_partner_by_id(*, partner_id: UUID) -> Partner | None:
    return Partner.all_objects.filter(pk=partner_id, is_active=True).first()


def get_image_url(object_key: str) -> str:
    return build_media_url(object_key) if object_key else ""


def discount_label(*, percent: int) -> str:
    return f"{int(percent)}%OFF"


def category_label(category: str) -> str:
    try:
        return PartnerCategory(category).label
    except ValueError:
        return category.replace("_", " ").title()


def resolve_city_name(*, city_id: UUID) -> str:
    city = get_city_by_id(city_id)
    return city.name if city is not None else ""


def viewer_partner_access(*, viewer: User | None) -> str:
    """
    Map membership to guidebook UI access:
    - member / city founder / staff → member (Show QR)
    - non-member → locked (Members Only)
    - anonymous → locked
    """
    if viewer is None or not getattr(viewer, "is_authenticated", False):
        return "locked"
    if viewer.is_platform_admin or viewer.is_superadmin or viewer.is_staff:
        return "member"
    if viewer.role in {
        User.Role.MEMBER,
        User.Role.CITY_FOUNDER,
        User.Role.TEAM_MEMBER,
    }:
        return "member"
    return "locked"


def resolve_city_id_for_request(
    *,
    city_id: UUID | None,
    community_id: UUID | None,
    user: User | None,
) -> UUID | None:
    if city_id is not None:
        return city_id
    if community_id is not None:
        community = get_community_by_id(community_id)
        if community is not None:
            return community.city_id
    if user is not None and getattr(user, "is_authenticated", False):
        if user.active_community_id:
            community = get_community_by_id(user.active_community_id)
            if community is not None:
                return community.city_id
    return None
