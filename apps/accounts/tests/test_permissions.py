from __future__ import annotations

from uuid import uuid4

import pytest
from rest_framework.test import APIRequestFactory

from apps.accounts.models import CommunityMembership, User
from apps.accounts.permissions import (
    CommunityFounderOnlyPermission,
    CommunityReadPermission,
    CommunityWritePermission,
    DenyTeamMemberFinancialAccess,
    HasMemberSocialAccess,
    IsCityFounder,
    IsMember,
    IsMobileAppUser,
    IsNonMember,
    IsObjectOwner,
    IsObjectOwnerOrCommunityWriter,
    IsPlatformAdmin,
    IsRegisteredUser,
    IsTeamMember,
    TeamMemberReadOnlyPermission,
)
from apps.accounts.role_checks import (
    get_effective_role_in_community,
    user_can_read_community,
    user_can_write_community,
    user_is_community_city_founder,
)
from tests.factories import CommunityFactory, CommunityMembershipFactory, UserFactory


class DummyTenantObject:
    def __init__(self, *, community_id, user_id=None):
        self.community_id = community_id
        self.user_id = user_id


@pytest.fixture
def community(db):
    return CommunityFactory()


@pytest.fixture
def request_factory():
    return APIRequestFactory()


def _request_with_user(user, method="GET"):
    factory = APIRequestFactory()
    django_request = getattr(factory, method.lower())("/")
    django_request.user = user
    return django_request


@pytest.mark.django_db
def test_platform_role_permissions(community):
    admin = UserFactory(admin=True)
    founder = UserFactory(city_founder=True)
    team_member = UserFactory(team_member=True)
    member = UserFactory(member=True)
    non_member = UserFactory(non_member=True)

    assert IsPlatformAdmin().has_permission(_request_with_user(admin), None) is True
    assert IsPlatformAdmin().has_permission(_request_with_user(founder), None) is False

    assert IsCityFounder().has_permission(_request_with_user(founder), None) is True
    assert IsCityFounder().has_permission(_request_with_user(team_member), None) is False

    assert IsTeamMember().has_permission(_request_with_user(team_member), None) is True
    assert IsMember().has_permission(_request_with_user(member), None) is True
    assert IsNonMember().has_permission(_request_with_user(non_member), None) is True

    assert IsRegisteredUser().has_permission(_request_with_user(non_member), None) is True
    assert IsMobileAppUser().has_permission(_request_with_user(founder), None) is True
    assert IsMobileAppUser().has_permission(_request_with_user(team_member), None) is False


@pytest.mark.django_db
def test_member_social_access_includes_city_founder():
    founder = UserFactory(city_founder=True)
    non_member = UserFactory(non_member=True)

    assert HasMemberSocialAccess().has_permission(_request_with_user(founder), None) is True
    assert HasMemberSocialAccess().has_permission(_request_with_user(non_member), None) is False


@pytest.mark.django_db
def test_effective_role_prefers_community_membership(community):
    user = UserFactory(member=True)
    CommunityMembershipFactory(
        user=user,
        community=community,
        role=CommunityMembership.Role.CITY_FOUNDER,
    )

    assert get_effective_role_in_community(user, community.id) == CommunityMembership.Role.CITY_FOUNDER
    assert user_can_write_community(user, community.id) is True


@pytest.mark.django_db
def test_team_member_can_read_but_not_write_community(community):
    user = UserFactory(team_member=True)
    CommunityMembershipFactory(
        user=user,
        community=community,
        role=CommunityMembership.Role.TEAM_MEMBER,
    )
    obj = DummyTenantObject(community_id=community.id)

    read_request = _request_with_user(user, "GET")
    write_request = _request_with_user(user, "POST")

    assert user_can_read_community(user, community.id) is True
    assert user_can_write_community(user, community.id) is False
    assert CommunityReadPermission().has_object_permission(read_request, None, obj) is True
    assert CommunityWritePermission().has_object_permission(write_request, None, obj) is False
    assert TeamMemberReadOnlyPermission().has_object_permission(write_request, None, obj) is False


@pytest.mark.django_db
def test_city_founder_can_write_own_community(community):
    user = UserFactory(city_founder=True)
    CommunityMembershipFactory(
        user=user,
        community=community,
        role=CommunityMembership.Role.CITY_FOUNDER,
    )
    obj = DummyTenantObject(community_id=community.id)
    request = _request_with_user(user, "PATCH")

    assert user_is_community_city_founder(user, community.id) is True
    assert CommunityFounderOnlyPermission().has_object_permission(request, None, obj) is True
    assert CommunityWritePermission().has_object_permission(request, None, obj) is True


@pytest.mark.django_db
def test_admin_cross_tenant_access(community):
    admin = UserFactory(admin=True)
    other_community_id = uuid4()
    obj = DummyTenantObject(community_id=other_community_id)
    request = _request_with_user(admin, "DELETE")

    assert CommunityWritePermission().has_object_permission(request, None, obj) is True


@pytest.mark.django_db
def test_member_cannot_access_other_community_without_membership(community):
    user = UserFactory(member=True)
    other_community_id = uuid4()

    assert user_can_read_community(user, other_community_id) is False
    assert user_can_write_community(user, other_community_id) is False


@pytest.mark.django_db
def test_member_can_read_own_community(community):
    user = UserFactory(member=True)
    CommunityMembershipFactory(
        user=user,
        community=community,
        role=CommunityMembership.Role.MEMBER,
    )

    assert user_can_read_community(user, community.id) is True
    assert user_can_write_community(user, community.id) is False


@pytest.mark.django_db
def test_is_object_owner(community):
    user = UserFactory(member=True)
    other = UserFactory(member=True)
    obj = DummyTenantObject(community_id=community.id, user_id=user.id)

    assert IsObjectOwner().has_object_permission(_request_with_user(user, "GET"), None, obj) is True
    assert IsObjectOwner().has_object_permission(_request_with_user(other, "GET"), None, obj) is False


@pytest.mark.django_db
def test_object_owner_or_community_writer(community):
    founder = UserFactory(city_founder=True)
    member = UserFactory(member=True)
    CommunityMembershipFactory(
        user=founder,
        community=community,
        role=CommunityMembership.Role.CITY_FOUNDER,
    )
    CommunityMembershipFactory(
        user=member,
        community=community,
        role=CommunityMembership.Role.MEMBER,
    )
    obj = DummyTenantObject(community_id=community.id, user_id=member.id)

    assert (
        IsObjectOwnerOrCommunityWriter().has_object_permission(
            _request_with_user(member, "PATCH"),
            None,
            obj,
        )
        is True
    )
    assert (
        IsObjectOwnerOrCommunityWriter().has_object_permission(
            _request_with_user(founder, "PATCH"),
            None,
            obj,
        )
        is True
    )


@pytest.mark.django_db
def test_deny_team_member_financial_access(community):
    team_member = UserFactory(team_member=True)
    CommunityMembershipFactory(
        user=team_member,
        community=community,
        role=CommunityMembership.Role.TEAM_MEMBER,
    )
    founder = UserFactory(city_founder=True)
    CommunityMembershipFactory(
        user=founder,
        community=community,
        role=CommunityMembership.Role.CITY_FOUNDER,
    )

    team_request = _request_with_user(team_member, "GET")
    team_request.community_id = community.id
    founder_request = _request_with_user(founder, "GET")
    founder_request.community_id = community.id

    assert DenyTeamMemberFinancialAccess().has_permission(team_request, None) is False
    assert DenyTeamMemberFinancialAccess().has_permission(founder_request, None) is True


@pytest.mark.django_db
def test_user_model_role_helpers():
    user = UserFactory(member=True)

    assert user.is_paid_member is True
    assert user.is_registered_user is True
    assert user.role == User.Role.MEMBER
