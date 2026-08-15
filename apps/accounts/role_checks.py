from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from apps.accounts.models import CommunityMembership, User

if TYPE_CHECKING:
    from rest_framework.request import Request
    from rest_framework.views import APIView


# Roles that bypass tenant boundaries (PRD: Admin + System).
CROSS_TENANT_ROLES = frozenset({User.Role.ADMIN})

# City Founder dashboard actors.
DASHBOARD_ROLES = frozenset(
    {
        User.Role.ADMIN,
        User.Role.CITY_FOUNDER,
        User.Role.TEAM_MEMBER,
    }
)

# Roles allowed to sign into the shared web dashboard (login page).
WEB_DASHBOARD_LOGIN_ROLES = frozenset(
    {
        User.Role.ADMIN,
        User.Role.CITY_FOUNDER,
    }
)

# Mobile app actors (City Founders also use mobile for social).
MOBILE_APP_ROLES = frozenset(
    {
        User.Role.MEMBER,
        User.Role.NON_MEMBER,
        User.Role.CITY_FOUNDER,
    }
)

# Registered users = any verified account with a consumer role or higher.
REGISTERED_USER_ROLES = frozenset(
    {
        User.Role.MEMBER,
        User.Role.NON_MEMBER,
        User.Role.CITY_FOUNDER,
        User.Role.TEAM_MEMBER,
        User.Role.ADMIN,
    }
)

# Community roles that may write tenant-scoped founder resources.
COMMUNITY_WRITE_ROLES = frozenset(
    {
        CommunityMembership.Role.ADMIN,
        CommunityMembership.Role.CITY_FOUNDER,
    }
)

# Community roles with dashboard read access (Team Member = read-only subset).
COMMUNITY_DASHBOARD_READ_ROLES = frozenset(
    {
        CommunityMembership.Role.ADMIN,
        CommunityMembership.Role.CITY_FOUNDER,
        CommunityMembership.Role.TEAM_MEMBER,
    }
)


def get_membership_for_user(user: User, community_id: UUID) -> CommunityMembership | None:
    return CommunityMembership.objects.filter(
        user_id=user.pk,
        community_id=community_id,
    ).first()


def get_effective_role_in_community(user: User, community_id: UUID) -> str:
    if user.role == User.Role.ADMIN:
        return User.Role.ADMIN

    membership = get_membership_for_user(user, community_id)
    if membership is not None:
        return membership.role

    return user.role


def user_has_platform_role(user: User, *roles: str) -> bool:
    return user.is_authenticated and user.role in roles


def user_can_access_web_dashboard(user: User) -> bool:
    """Admin / City Founder web dashboard (shared login). Superadmin always allowed."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.role in WEB_DASHBOARD_LOGIN_ROLES


def user_is_registered(user: User) -> bool:
    return user.is_authenticated and user.role in REGISTERED_USER_ROLES


def user_has_member_social_access(user: User) -> bool:
    if user.is_platform_admin:
        return True
    return user.role in {User.Role.MEMBER, User.Role.CITY_FOUNDER}


def user_can_read_community(user: User, community_id: UUID) -> bool:
    if user.is_platform_admin:
        return True

    effective_role = get_effective_role_in_community(user, community_id)
    if effective_role in CROSS_TENANT_ROLES:
        return True
    if effective_role in COMMUNITY_DASHBOARD_READ_ROLES:
        return True
    if effective_role in {User.Role.MEMBER, User.Role.NON_MEMBER, CommunityMembership.Role.MEMBER}:
        return get_membership_for_user(user, community_id) is not None
    return False


def user_can_write_community(user: User, community_id: UUID) -> bool:
    if user.is_platform_admin:
        return True

    effective_role = get_effective_role_in_community(user, community_id)
    return effective_role in COMMUNITY_WRITE_ROLES


def user_is_community_city_founder(user: User, community_id: UUID) -> bool:
    if user.is_platform_admin:
        return True

    effective_role = get_effective_role_in_community(user, community_id)
    return effective_role in {User.Role.CITY_FOUNDER, CommunityMembership.Role.CITY_FOUNDER}


def user_is_community_team_member(user: User, community_id: UUID) -> bool:
    effective_role = get_effective_role_in_community(user, community_id)
    return effective_role in {User.Role.TEAM_MEMBER, CommunityMembership.Role.TEAM_MEMBER}


def get_object_community_id(obj: object) -> UUID | None:
    community_id = getattr(obj, "community_id", None)
    if community_id is not None:
        return community_id
    return None


def get_request_community_id(request: Request, view: APIView) -> UUID | None:
    community_id = getattr(request, "community_id", None)
    if community_id is not None:
        return community_id

    kwargs = getattr(view, "kwargs", {}) or {}
    raw_community_id = kwargs.get("community_id")
    if raw_community_id:
        return UUID(str(raw_community_id))

    from core.tenancy import get_tenant_context

    tenant = get_tenant_context()
    if tenant is not None:
        return tenant.community_id

    return None
