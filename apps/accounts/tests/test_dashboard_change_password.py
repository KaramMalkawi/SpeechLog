from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.adminpanel.models import AdminAuditLog
from tests.factories import UserFactory

URL = reverse("dashboard-change-password")


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    user = UserFactory(email="admin.pw@example.com", full_name="Admin PW", admin=True)
    user.set_password("OldPass123!")
    user.save(update_fields=["password"])
    return user


@pytest.mark.django_db
def test_admin_can_change_password(api_client, admin_user):
    token = RefreshToken.for_user(admin_user).access_token
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = api_client.post(
        URL,
        {
            "current_password": "OldPass123!",
            "new_password": "NewPass123!",
        },
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    admin_user.refresh_from_db()
    assert admin_user.check_password("NewPass123!")
    assert AdminAuditLog.objects.filter(
        action=AdminAuditLog.Action.PASSWORD_CHANGE,
        actor=admin_user,
    ).exists()


@pytest.mark.django_db
def test_admin_change_password_rejects_wrong_current(api_client, admin_user):
    token = RefreshToken.for_user(admin_user).access_token
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = api_client.post(
        URL,
        {
            "current_password": "WrongPass!",
            "new_password": "NewPass123!",
        },
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    admin_user.refresh_from_db()
    assert admin_user.check_password("OldPass123!")


@pytest.mark.django_db
def test_member_cannot_change_dashboard_password(api_client):
    member = UserFactory(email="member.pw@example.com", member=True)
    member.set_password("OldPass123!")
    member.save(update_fields=["password"])
    token = RefreshToken.for_user(member).access_token
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = api_client.post(
        URL,
        {
            "current_password": "OldPass123!",
            "new_password": "NewPass123!",
        },
        format="json",
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
