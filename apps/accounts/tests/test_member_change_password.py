from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from tests.factories import UserFactory

URL = reverse("me-change-password")


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def member(db):
    user = UserFactory(email="member.pw@example.com", full_name="Member PW")
    user.set_password("OldPass123!")
    user.email_verified = True
    user.save(update_fields=["password", "email_verified"])
    return user


@pytest.mark.django_db
def test_member_can_change_password(api_client, member):
    token = RefreshToken.for_user(member).access_token
    response = api_client.post(
        URL,
        {"current_password": "OldPass123!", "new_password": "NewPass123!"},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert response.status_code == status.HTTP_200_OK
    member.refresh_from_db()
    assert member.check_password("NewPass123!")


@pytest.mark.django_db
def test_member_change_password_rejects_wrong_current(api_client, member):
    token = RefreshToken.for_user(member).access_token
    response = api_client.post(
        URL,
        {"current_password": "WrongPass123!", "new_password": "NewPass123!"},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    member.refresh_from_db()
    assert member.check_password("OldPass123!")
