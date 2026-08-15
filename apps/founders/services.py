from __future__ import annotations

from uuid import UUID

from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.accounts.services import (
    delete_user_account,
    email_is_taken,
    generate_temporary_password,
    provision_city_founder_user,
    update_user_account_fields,
)
from apps.adminpanel.services import (
    CITY_FOUNDER_CREATE_ACTION,
    CITY_FOUNDER_DELETE_ACTION,
    CITY_FOUNDER_UPDATE_ACTION,
    record_admin_audit_event,
)
from apps.founders.models import Founder
from apps.founders.selectors import get_city_founder_by_id, get_city_founder_by_user_id
from apps.tenancy.selectors import get_city_by_id


class CityFounderNotFound(Exception):
    """City founder profile does not exist."""


class CityFounderDeleteConfirmationError(Exception):
    """Delete confirmation name does not match."""


def _serialize_city_context(city) -> dict:
    return {
        "city_id": city.id,
        "city_name": city.name,
        "country_id": city.country_id,
        "country_name": city.country.name,
        "country_code": city.country.code,
    }


def city_founder_to_payload(founder: Founder, *, city=None) -> dict:
    if city is None:
        city = get_city_by_id(founder.city_id)
    user = founder.user
    payload = {
        "id": founder.id,
        "user_id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "status": founder.status,
        "created_at": founder.created_at,
        "city_id": founder.city_id,
        "city_name": "",
        "country_id": None,
        "country_name": "",
        "country_code": "",
    }
    if city is not None:
        payload.update(_serialize_city_context(city))
    return payload


def city_has_assigned_founder(*, city_id: UUID, exclude_founder_id: UUID | None = None) -> bool:
    qs = Founder.objects.filter(
        city_id=city_id,
        status__in=Founder.OCCUPYING_STATUSES,
    )
    if exclude_founder_id is not None:
        qs = qs.exclude(pk=exclude_founder_id)
    return qs.exists()


def mark_founder_active_after_first_login(*, user_id: UUID | str) -> bool:
    """Promote pending founders to active on their first successful login."""
    updated = Founder.objects.filter(
        user_id=user_id,
        status=Founder.Status.PENDING_FIRST_LOGIN,
    ).update(status=Founder.Status.ACTIVE)
    return updated > 0


def deactivate_founder_profile_for_user(*, user_id: UUID | str) -> bool:
    """Mark a founder profile inactive when the user loses the City Founder role.

    Keeps the profile row (audit/history) but frees the city's single-founder slot
    and removes it from active listings.
    """
    updated = (
        Founder.objects.filter(user_id=user_id)
        .exclude(status=Founder.Status.INACTIVE)
        .update(status=Founder.Status.INACTIVE)
    )
    return updated > 0


@transaction.atomic
def assign_or_update_founder_for_user(
    *,
    actor_id: UUID | str,
    user_id: UUID,
    city_id: UUID,
    status: str | None = None,
) -> Founder:
    """Create or update the Founder profile for a user with the City Founder role."""
    city = get_city_by_id(city_id)
    if city is None or not city.is_active:
        raise DRFValidationError({"city_id": "Select a valid active city."})

    if status is not None and status not in Founder.Status.values:
        raise DRFValidationError({"founder_status": "Invalid status."})

    founder = get_city_founder_by_user_id(user_id)
    if founder is None:
        desired_status = status or Founder.Status.PENDING_FIRST_LOGIN
        if desired_status in Founder.OCCUPYING_STATUSES and city_has_assigned_founder(
            city_id=city.id
        ):
            raise DRFValidationError(
                {"city_id": "This city already has an active City Founder."}
            )
        founder = Founder.objects.create(
            user_id=user_id,
            city_id=city.id,
            status=desired_status,
        )
        record_admin_audit_event(
            actor_id=actor_id,
            action=CITY_FOUNDER_CREATE_ACTION,
            metadata={
                "city_founder_id": str(founder.id),
                "user_id": str(user_id),
                "city_id": str(city.id),
                "status": founder.status,
                "source": "user_admin_update",
            },
        )
        return founder

    return update_city_founder(
        actor_id=actor_id,
        founder_id=founder.id,
        city_id=city.id,
        status=status,
    )


def get_founder_dashboard_overview(*, user_id: UUID | str) -> dict:
    """Empty overview payload for the City Founder web dashboard."""
    founder = get_city_founder_by_user_id(UUID(str(user_id)))
    if founder is None:
        raise CityFounderNotFound()

    city = get_city_by_id(founder.city_id)
    full_name = (founder.user.full_name or "").strip() or founder.user.email
    return {
        "full_name": full_name,
        "email": founder.user.email,
        "status": founder.status,
        "city_id": founder.city_id,
        "city_name": city.name if city else "",
        "country_name": city.country.name if city else "",
        "welcome_message": f"Welcome, {full_name}",
    }


@transaction.atomic
def create_city_founder(
    *,
    actor_id: UUID | str,
    full_name: str,
    email: str,
    city_id: UUID,
) -> tuple[Founder, str]:
    city = get_city_by_id(city_id)
    if city is None or not city.is_active:
        raise DRFValidationError({"city_id": "Select a valid active city."})

    if email_is_taken(email=email):
        raise DRFValidationError({"email": "A user with this email already exists."})

    if city_has_assigned_founder(city_id=city.id):
        raise DRFValidationError({"city_id": "This city already has an active City Founder."})

    temporary_password = generate_temporary_password()
    try:
        user = provision_city_founder_user(
            full_name=full_name,
            email=email,
            password=temporary_password,
        )
    except ValueError as exc:
        raise DRFValidationError({"email": str(exc)}) from exc

    try:
        founder = Founder.objects.create(
            user=user,
            city_id=city.id,
            status=Founder.Status.PENDING_FIRST_LOGIN,
        )
    except IntegrityError as exc:
        raise DRFValidationError(
            {"city_id": "This city already has an active City Founder."}
        ) from exc

    record_admin_audit_event(
        actor_id=actor_id,
        action=CITY_FOUNDER_CREATE_ACTION,
        metadata={
            "city_founder_id": str(founder.id),
            "user_id": str(user.id),
            "email": user.email,
            "city_id": str(city.id),
            "status": founder.status,
        },
    )
    return founder, temporary_password


@transaction.atomic
def update_city_founder(
    *,
    actor_id: UUID | str,
    founder_id: UUID,
    full_name: str | None = None,
    email: str | None = None,
    city_id: UUID | None = None,
    status: str | None = None,
) -> Founder:
    founder = get_city_founder_by_id(founder_id)
    if founder is None:
        raise CityFounderNotFound()

    if city_id is not None:
        city = get_city_by_id(city_id)
        if city is None or not city.is_active:
            raise DRFValidationError({"city_id": "Select a valid active city."})
        becoming_or_staying_assigned = (
            status in Founder.OCCUPYING_STATUSES
            if status is not None
            else founder.status in Founder.OCCUPYING_STATUSES
        )
        if becoming_or_staying_assigned and city_has_assigned_founder(
            city_id=city.id,
            exclude_founder_id=founder.pk,
        ):
            raise DRFValidationError(
                {"city_id": "This city already has an active City Founder."}
            )
        founder.city_id = city.id

    is_active: bool | None = None
    if status is not None:
        if status not in Founder.Status.values:
            raise DRFValidationError({"status": "Invalid status."})
        if status in Founder.OCCUPYING_STATUSES and city_has_assigned_founder(
            city_id=founder.city_id,
            exclude_founder_id=founder.pk,
        ):
            raise DRFValidationError(
                {"status": "This city already has an active City Founder."}
            )
        founder.status = status
        is_active = status != Founder.Status.SUSPENDED

    try:
        user = update_user_account_fields(
            user_id=founder.user_id,
            full_name=full_name,
            email=email,
            is_active=is_active,
        )
    except ValueError as exc:
        raise DRFValidationError({"email": str(exc)}) from exc

    founder.save()
    founder.user = user

    record_admin_audit_event(
        actor_id=actor_id,
        action=CITY_FOUNDER_UPDATE_ACTION,
        metadata={
            "city_founder_id": str(founder.id),
            "user_id": str(user.id),
            "email": user.email,
            "city_id": str(founder.city_id),
            "status": founder.status,
        },
    )
    return founder


@transaction.atomic
def delete_city_founder(
    *,
    actor_id: UUID | str,
    founder_id: UUID,
    confirmation_name: str,
) -> None:
    founder = get_city_founder_by_id(founder_id)
    if founder is None:
        raise CityFounderNotFound()

    expected = founder.user.full_name.strip()
    if confirmation_name.strip() != expected:
        raise CityFounderDeleteConfirmationError(
            "Type the City Founder's full name exactly to confirm deletion."
        )

    user = founder.user
    metadata = {
        "city_founder_id": str(founder.id),
        "user_id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "city_id": str(founder.city_id),
    }

    # Cascade deletes Founder via OneToOne.
    delete_user_account(user_id=user.id)

    record_admin_audit_event(
        actor_id=actor_id,
        action=CITY_FOUNDER_DELETE_ACTION,
        metadata=metadata,
    )
