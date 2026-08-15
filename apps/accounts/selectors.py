from __future__ import annotations

from uuid import UUID

from django.db.models import Case, IntegerField, Q, QuerySet, Value, When

from apps.accounts.models import CommunityMembership, User


def get_user_by_id(user_id: UUID) -> User | None:
    return User.objects.filter(pk=user_id).first()


def get_user_by_email(email: str) -> User | None:
    return User.objects.filter(email=User.objects.normalize_email(email)).first()


def get_user_membership(user_id: UUID, community_id: UUID) -> CommunityMembership | None:
    return CommunityMembership.objects.filter(
        user_id=user_id,
        community_id=community_id,
    ).first()


def admin_user_queryset() -> QuerySet[User]:
    return User.objects.select_related("founder_profile").all()


def list_users_for_admin(
    *,
    actor_id: UUID | str | None = None,
    role: str | None = None,
    search: str | None = None,
) -> list[User]:
    qs = admin_user_queryset()
    if role:
        qs = qs.filter(role=role)
    if search:
        term = search.strip()
        if term:
            qs = qs.filter(Q(full_name__icontains=term) | Q(email__icontains=term))

    if actor_id is not None:
        qs = qs.annotate(
            is_current_user=Case(
                When(pk=actor_id, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        ).order_by("is_current_user", "full_name", "email")
    else:
        qs = qs.order_by("full_name", "email")

    return list(qs)


def list_platform_admins_for_admin(
    *,
    actor_id: UUID | str | None = None,
    status: str | None = None,
    search: str | None = None,
) -> list[User]:
    """Platform Admins and Superadmins for the Admins management screen."""
    qs = admin_user_queryset().filter(Q(role=User.Role.ADMIN) | Q(is_superuser=True))

    if search:
        term = search.strip()
        if term:
            qs = qs.filter(Q(full_name__icontains=term) | Q(email__icontains=term))

    users = list(qs)
    if status and status != "All":
        from apps.accounts.services import platform_admin_status

        users = [u for u in users if platform_admin_status(u) == status]

    if actor_id is not None:
        users.sort(
            key=lambda u: (
                0 if str(u.id) == str(actor_id) else 1,
                (u.full_name or "").lower(),
                u.email.lower(),
            )
        )
    else:
        users.sort(key=lambda u: ((u.full_name or "").lower(), u.email.lower()))

    return users
