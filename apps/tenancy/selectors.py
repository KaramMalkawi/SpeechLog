from __future__ import annotations

from uuid import UUID

from django.conf import settings

from apps.tenancy.country_data import (
    CountryInfo,
    list_nationality_countries,
    list_residence_countries,
)
from apps.tenancy.models import City, Community, Country


def get_nationality_countries() -> list[CountryInfo]:
    return list_nationality_countries()


def get_residence_countries() -> list[CountryInfo]:
    return list_residence_countries(allowed_codes=settings.RESIDENCE_COUNTRY_CODES)


def list_operational_countries(*, active_only: bool = True) -> list[Country]:
    qs = Country.objects.all().order_by("name")
    if active_only:
        qs = qs.filter(is_active=True)
    return list(qs)


def list_cities_for_country(*, country_id: UUID, active_only: bool = True) -> list[City]:
    qs = City.objects.filter(country_id=country_id).select_related("country").order_by("name")
    if active_only:
        qs = qs.filter(is_active=True)
    return list(qs)


def get_city_by_id(city_id: UUID) -> City | None:
    return City.objects.select_related("country").filter(pk=city_id).first()


def get_country_by_id(country_id: UUID) -> Country | None:
    return Country.objects.filter(pk=country_id).first()


def get_community_by_id(community_id: UUID) -> Community | None:
    return (
        Community.objects.select_related("city")
        .filter(pk=community_id, is_active=True)
        .first()
    )


def get_default_community() -> Community | None:
    """Return the home community for users who have not picked one yet.

    Prefers an active GENERAL community matching ``DEFAULT_COMMUNITY_SLUG``
    (when set), otherwise the first active GENERAL community by name.
    """
    preferred_slug = getattr(settings, "DEFAULT_COMMUNITY_SLUG", "") or ""
    qs = Community.objects.select_related("city").filter(
        is_active=True,
        community_type=Community.CommunityType.GENERAL,
    )
    if preferred_slug:
        community = qs.filter(slug=preferred_slug).first()
        if community is not None:
            return community
    return qs.order_by("name").first()
