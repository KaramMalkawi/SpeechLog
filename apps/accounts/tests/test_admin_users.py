from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.adminpanel.models import AdminAuditLog
from tests.factories import UserFactory

LIST_URL = reverse("admin-user-list")


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    user = UserFactory(
        email="admin.users@example.com",
        full_name="Admin User",
        admin=True,
    )
    user.set_password("Str0ngPass!")
    user.save(update_fields=["password"])
    return user


@pytest.fixture
def auth_client(api_client, admin_user):
    token = RefreshToken.for_user(admin_user).access_token
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api_client


@pytest.mark.django_db
def test_admin_list_users_puts_current_user_first(auth_client, admin_user):
    member = UserFactory(email="member.users@example.com", full_name="Zed Member", member=True)
    founder = UserFactory(
        email="founder.users@example.com",
        full_name="Ann Founder",
        city_founder=True,
    )

    response = auth_client.get(LIST_URL)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) >= 3
    assert response.data[0]["id"] == str(admin_user.id)
    assert response.data[0]["is_current_user"] is True
    assert response.data[0]["can_delete"] is False

    ids = {row["id"] for row in response.data}
    assert str(member.id) in ids
    assert str(founder.id) in ids


@pytest.mark.django_db
def test_admin_cannot_delete_self(auth_client, admin_user):
    response = auth_client.delete(
        reverse("admin-user-detail", kwargs={"user_id": admin_user.id}),
        {"confirmation_name": admin_user.full_name},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert User.objects.filter(pk=admin_user.id).exists()


@pytest.mark.django_db
def test_admin_cannot_delete_superuser(auth_client):
    superuser = UserFactory(
        email="super.users@example.com",
        full_name="Super Admin",
        admin=True,
        is_superuser=True,
        is_staff=True,
    )
    response = auth_client.delete(
        reverse("admin-user-detail", kwargs={"user_id": superuser.id}),
        {"confirmation_name": superuser.full_name},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Superadmin" in response.data["detail"]
    assert User.objects.filter(pk=superuser.id).exists()


@pytest.mark.django_db
def test_admin_can_delete_other_user(auth_client, admin_user):
    target = UserFactory(
        email="delete.me@example.com",
        full_name="Delete Me",
        member=True,
    )
    response = auth_client.delete(
        reverse("admin-user-detail", kwargs={"user_id": target.id}),
        {"confirmation_name": "Delete Me"},
        format="json",
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not User.objects.filter(pk=target.id).exists()
    assert AdminAuditLog.objects.filter(action=AdminAuditLog.Action.USER_DELETE).exists()


@pytest.mark.django_db
def test_member_cannot_list_users(api_client):
    member = UserFactory(email="member.nolist@example.com", member=True)
    token = RefreshToken.for_user(member).access_token
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = api_client.get(LIST_URL)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_admin_can_update_user_role_and_syncs_flags(auth_client):
    target = UserFactory(email="promote.me@example.com", full_name="Promote Me", member=True)
    response = auth_client.patch(
        reverse("admin-user-detail", kwargs={"user_id": target.id}),
        {"role": User.Role.ADMIN},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["role"] == User.Role.ADMIN

    target.refresh_from_db()
    assert target.role == User.Role.ADMIN
    assert target.is_staff is False
    assert target.is_superuser is False
    assert not target.groups.exists()
    assert not target.user_permissions.exists()
    assert AdminAuditLog.objects.filter(
        action=AdminAuditLog.Action.USER_ROLE_UPDATE
    ).exists()


@pytest.mark.django_db
def test_admin_cannot_change_own_role(auth_client, admin_user):
    response = auth_client.patch(
        reverse("admin-user-detail", kwargs={"user_id": admin_user.id}),
        {"role": User.Role.MEMBER},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    admin_user.refresh_from_db()
    assert admin_user.role == User.Role.ADMIN


@pytest.mark.django_db
def test_admin_cannot_change_superuser_role(auth_client):
    superuser = UserFactory(
        email="super.role@example.com",
        full_name="Super Admin",
        admin=True,
        is_superuser=True,
        is_staff=True,
    )
    response = auth_client.patch(
        reverse("admin-user-detail", kwargs={"user_id": superuser.id}),
        {"role": User.Role.MEMBER},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    superuser.refresh_from_db()
    assert superuser.role == User.Role.ADMIN


@pytest.mark.django_db
def test_admin_reject_invalid_role(auth_client):
    target = UserFactory(email="bad.role@example.com", member=True)
    response = auth_client.patch(
        reverse("admin-user-detail", kwargs={"user_id": target.id}),
        {"role": "wizard"},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_demoting_city_founder_deactivates_profile(auth_client):
    from apps.founders.models import Founder

    founder_user = UserFactory(
        email="founder.demote@example.com",
        full_name="Demote Founder",
        city_founder=True,
    )
    founder = Founder.objects.create(
        user=founder_user,
        city_id="00000000-0000-0000-0000-000000000abc",
        status=Founder.Status.ACTIVE,
    )
    response = auth_client.patch(
        reverse("admin-user-detail", kwargs={"user_id": founder_user.id}),
        {"role": User.Role.MEMBER},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    founder.refresh_from_db()
    assert founder.status == Founder.Status.INACTIVE
    founder_user.refresh_from_db()
    assert founder_user.role == User.Role.MEMBER
