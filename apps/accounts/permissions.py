from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.models import User
from apps.accounts.role_checks import (
    DASHBOARD_ROLES,
    MOBILE_APP_ROLES,
    get_object_community_id,
    get_request_community_id,
    user_can_read_community,
    user_can_write_community,
    user_has_member_social_access,
    user_has_platform_role,
    user_is_community_city_founder,
    user_is_community_team_member,
    user_is_registered,
)

if TYPE_CHECKING:
    from rest_framework.request import Request
    from rest_framework.views import APIView


def _authenticated_user(request: Request) -> User | None:
    user = request.user
    if user and user.is_authenticated:
        return user
    return None


class IsIdentityVerified(BasePermission):
    """Historically required Didit identity verification; now email verification
    alone is enough. Identity verification is optional for now and will resurface
    later as a soft, per-action recommendation rather than a hard gate."""

    message = "Email verification is required to access this resource."

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = _authenticated_user(request)
        if user is None:
            return False
        if user.is_platform_admin:
            return True
        return user.email_verified


class IsRegisteredUser(BasePermission):
    """Any authenticated, email-verified consumer account (Member or Non-Member+)."""

    message = "A registered account is required."

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = _authenticated_user(request)
        if user is None:
            return False
        if user.is_platform_admin:
            return True
        return user.email_verified and user_is_registered(user)


class HasPlatformRole(BasePermission):
    """View-level check against User.role. Admins bypass by default."""

    allowed_roles: frozenset[str] = frozenset()
    allow_admin_bypass: bool = True
    message = "You do not have permission to perform this action."

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = _authenticated_user(request)
        if user is None:
            return False
        if self.allow_admin_bypass and user.is_platform_admin:
            return True
        return user_has_platform_role(user, *self.allowed_roles)


class IsPlatformAdmin(BasePermission):
    message = "Admin access is required."

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = _authenticated_user(request)
        if user is None:
            return False
        return user.is_platform_admin or user.is_superadmin


class FounderPasswordChanged(BasePermission):
    """City Founders with a temporary password must change it before other actions."""

    message = "You must change your password before continuing."

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = _authenticated_user(request)
        if user is None:
            return False
        if user.role != User.Role.CITY_FOUNDER:
            return True
        return not user.must_change_password


class IsCityFounder(HasPlatformRole):
    message = "City Founder access is required."
    allowed_roles = frozenset({User.Role.CITY_FOUNDER})


class IsTeamMember(HasPlatformRole):
    message = "Team Member access is required."
    allowed_roles = frozenset({User.Role.TEAM_MEMBER})


class IsMember(HasPlatformRole):
    message = "An active Member subscription is required."
    allowed_roles = frozenset({User.Role.MEMBER})


class IsNonMember(HasPlatformRole):
    message = "Non-Member access is required."
    allowed_roles = frozenset({User.Role.NON_MEMBER})


class IsDashboardUser(HasPlatformRole):
    message = "Dashboard access is required."
    allowed_roles = DASHBOARD_ROLES


class IsMobileAppUser(HasPlatformRole):
    message = "Mobile app access is required."
    allowed_roles = MOBILE_APP_ROLES


class HasMemberSocialAccess(BasePermission):
    """Member-level social actions; City Founders retain these on mobile."""

    message = "Member access is required for this action."

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = _authenticated_user(request)
        if user is None:
            return False
        return user_has_member_social_access(user)


class HasAnyPlatformRole(BasePermission):
    """OR-combination of platform roles."""

    def __init__(self, *roles: str, allow_admin_bypass: bool = True) -> None:
        self.allowed_roles = frozenset(roles)
        self.allow_admin_bypass = allow_admin_bypass

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = _authenticated_user(request)
        if user is None:
            return False
        if self.allow_admin_bypass and user.is_platform_admin:
            return True
        return user_has_platform_role(user, *self.allowed_roles)


class TenantObjectPermission(BasePermission):
    """Base object permission for tenant-scoped models carrying community_id."""

    message = "You do not have permission to access this resource in this community."

    def has_object_permission(self, request: Request, view: APIView, obj: object) -> bool:
        user = _authenticated_user(request)
        if user is None:
            return False
        if user.is_platform_admin:
            return True

        community_id = get_object_community_id(obj)
        if community_id is None:
            return False

        if request.method in SAFE_METHODS:
            return self.allow_read(user, community_id, request, view, obj)
        return self.allow_write(user, community_id, request, view, obj)

    def allow_read(
        self,
        user: User,
        community_id: UUID,
        request: Request,
        view: APIView,
        obj: object,
    ) -> bool:
        return user_can_read_community(user, community_id)

    def allow_write(
        self,
        user: User,
        community_id: UUID,
        request: Request,
        view: APIView,
        obj: object,
    ) -> bool:
        return user_can_write_community(user, community_id)


class CommunityReadPermission(TenantObjectPermission):
    """Read within own community for dashboard + mobile actors."""


class CommunityWritePermission(TenantObjectPermission):
    """Write within own community for Admin + City Founder only (not Team Member)."""

    def allow_read(
        self,
        user: User,
        community_id: UUID,
        request: Request,
        view: APIView,
        obj: object,
    ) -> bool:
        return user_can_write_community(user, community_id)

    def allow_write(
        self,
        user: User,
        community_id: UUID,
        request: Request,
        view: APIView,
        obj: object,
    ) -> bool:
        return user_can_write_community(user, community_id)


class CommunityFounderOnlyPermission(TenantObjectPermission):
    """City Founder (or Admin) only — team management, join-request approvals, etc."""

    message = "City Founder access is required for this community."

    def allow_read(
        self,
        user: User,
        community_id: UUID,
        request: Request,
        view: APIView,
        obj: object,
    ) -> bool:
        return user_is_community_city_founder(user, community_id)

    def allow_write(
        self,
        user: User,
        community_id: UUID,
        request: Request,
        view: APIView,
        obj: object,
    ) -> bool:
        return user_is_community_city_founder(user, community_id)


class TeamMemberReadOnlyPermission(TenantObjectPermission):
    """Team Members may read relevant dashboard sections but never write."""

    message = "Team Members have read-only access."

    def allow_read(
        self,
        user: User,
        community_id: UUID,
        request: Request,
        view: APIView,
        obj: object,
    ) -> bool:
        if user_is_community_city_founder(user, community_id):
            return True
        if user_is_community_team_member(user, community_id):
            return True
        return user_can_read_community(user, community_id)

    def allow_write(
        self,
        user: User,
        community_id: UUID,
        request: Request,
        view: APIView,
        obj: object,
    ) -> bool:
        if user_is_community_team_member(user, community_id):
            return False
        return user_can_write_community(user, community_id)


class IsObjectOwner(BasePermission):
    """Object-level owner check using a configurable attribute (default: user_id)."""

    owner_field = "user_id"
    message = "You can only access your own resources."

    def has_object_permission(self, request: Request, view: APIView, obj: object) -> bool:
        user = _authenticated_user(request)
        if user is None:
            return False
        if user.is_platform_admin:
            return True

        owner_id = getattr(obj, self.owner_field, None)
        if owner_id is None:
            return False
        return str(owner_id) == str(user.pk)


class IsObjectOwnerOrCommunityWriter(BasePermission):
    """Owner can access; City Founder/Admin can access objects in their community."""

    owner_field = "user_id"
    message = "You do not have permission to access this resource."

    def has_object_permission(self, request: Request, view: APIView, obj: object) -> bool:
        user = _authenticated_user(request)
        if user is None:
            return False
        if user.is_platform_admin:
            return True

        owner_id = getattr(obj, self.owner_field, None)
        if owner_id is not None and str(owner_id) == str(user.pk):
            return True

        community_id = get_object_community_id(obj)
        if community_id is None:
            return False

        if request.method in SAFE_METHODS:
            return user_can_read_community(user, community_id)
        return user_can_write_community(user, community_id)


class DenyTeamMemberFinancialAccess(BasePermission):
    """Blocks Team Members from financial/revenue endpoints (FR 185)."""

    message = "Team Members cannot access financial data."

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = _authenticated_user(request)
        if user is None:
            return False
        if user.is_platform_admin or user.role == User.Role.CITY_FOUNDER:
            return True

        community_id = get_request_community_id(request, view)
        if community_id is None:
            return user.role != User.Role.TEAM_MEMBER

        return not user_is_community_team_member(user, community_id)


def combine_permissions(*permissions: type[BasePermission]) -> list[type[BasePermission]]:
    """Helper for viewsets declaring stacked permission classes."""
    return list(permissions)
