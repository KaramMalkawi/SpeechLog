from __future__ import annotations

from uuid import UUID

from django.db.models import Q, QuerySet

from apps.founders.models import Founder, FounderApplication


def city_founder_queryset() -> QuerySet[Founder]:
    return Founder.objects.select_related("user").all()


def get_city_founder_by_user_id(user_id: UUID) -> Founder | None:
    return city_founder_queryset().filter(user_id=user_id).first()


def get_city_founder_by_id(founder_id: UUID) -> Founder | None:
    return city_founder_queryset().filter(pk=founder_id).first()


def list_city_founders(
    *,
    status: str | None = None,
    search: str | None = None,
) -> list[Founder]:
    qs = city_founder_queryset().order_by("-created_at")
    if status:
        qs = qs.filter(status=status)
    if search:
        term = search.strip()
        if term:
            qs = qs.filter(
                Q(user__full_name__icontains=term) | Q(user__email__icontains=term)
            )
    return list(qs)


def founder_application_queryset() -> QuerySet[FounderApplication]:
    return FounderApplication.objects.all()


def get_founder_application_by_id(application_id: UUID) -> FounderApplication | None:
    return founder_application_queryset().filter(pk=application_id).first()


def list_founder_applications(
    *,
    status: str | None = None,
    search: str | None = None,
) -> list[FounderApplication]:
    qs = founder_application_queryset().order_by(
        "-submitted_at",
        "-sheet_row",
    )
    if status:
        qs = qs.filter(status=status)
    if search:
        term = search.strip()
        if term:
            qs = qs.filter(
                Q(email__icontains=term)
                | Q(country_name__icontains=term)
                | Q(full_name__icontains=term)
            )
    return list(qs)
