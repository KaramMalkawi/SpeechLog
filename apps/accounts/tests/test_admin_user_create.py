from __future__ import annotations

from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.adminpanel.models import AdminAuditLog
from apps.founders.models import Founder
from tests.factories import CityFactory, CountryFactory, UserFactory

LIST_URL = reverse("admin-user-list")


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    user = UserFactory(admin=True, email="admin.creator@example.com", full_name="Creator Admin")
    user.set_password("Str0ngPass!")
    user.save(update_fields=["password"])
    return user


@pytest.fixture
def auth_client(api_client, admin_user):
    token = RefreshToken.for_user(admin_user).access_token
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api_client


@pytest.fixture
def city(db):
    country = CountryFactory()
    return CityFactory(country=country)


@pytest.mark.django_db
@patch("apps.accounts.admin_user_views.send_platform_admin_invite_email_task.delay")
def test_create_admin_user(mock_delay, auth_client):
    response = auth_client.post(
        LIST_URL,
        {
            "full_name": "New Admin",
            "email": "new.admin@example.com",
            "role": User.Role.ADMIN,
        },
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    user = User.objects.get(email="new.admin@example.com")
    assert user.role == User.Role.ADMIN
    assert user.must_change_password is True
    assert user.is_superuser is False
    mock_delay.assert_called_once()
    assert AdminAuditLog.objects.filter(action=AdminAuditLog.Action.ADMIN_CREATE).exists()


@pytest.mark.django_db
@patch("apps.accounts.admin_user_views.send_city_founder_invite_email_task.delay")
def test_create_city_founder_user(mock_delay, auth_client, city):
    response = auth_client.post(
        LIST_URL,
        {
            "full_name": "Omar Founder",
            "email": "omar.founder@example.com",
            "role": User.Role.CITY_FOUNDER,
            "city_id": str(city.id),
        },
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    user = User.objects.get(email="omar.founder@example.com")
    assert user.role == User.Role.CITY_FOUNDER
    assert Founder.objects.filter(user=user, city_id=city.id).exists()
    mock_delay.assert_called_once()


@pytest.mark.django_db
def test_create_city_founder_requires_city(auth_client):
    response = auth_client.post(
        LIST_URL,
        {
            "full_name": "No City",
            "email": "nocity@example.com",
            "role": User.Role.CITY_FOUNDER,
        },
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
@patch("apps.accounts.admin_user_views.send_platform_admin_invite_email_task.delay")
def test_create_member_user(mock_delay, auth_client):
    response = auth_client.post(
        LIST_URL,
        {
            "full_name": "New Member",
            "email": "new.member@example.com",
            "role": User.Role.MEMBER,
        },
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    user = User.objects.get(email="new.member@example.com")
    assert user.role == User.Role.MEMBER
    mock_delay.assert_called_once()
