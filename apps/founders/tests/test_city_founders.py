from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.adminpanel.models import AdminAuditLog
from apps.founders.models import Founder
from apps.accounts.services import generate_temporary_password
from tests.factories import CityFactory, CountryFactory, UserFactory

LIST_URL = reverse("city-founder-list")


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    # Platform Admin is role-based; is_staff is reserved for Django superadmin.
    user = UserFactory(admin=True, email="admin-founder@example.com")
    user.set_password("Str0ngPass!")
    user.save(update_fields=["password"])
    return user


@pytest.fixture
def auth_client(api_client, admin_user):
    token = RefreshToken.for_user(admin_user).access_token
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api_client


@pytest.fixture
def country(db):
    return CountryFactory()


@pytest.fixture
def city(country):
    return CityFactory(country=country)


def test_generate_temporary_password_is_valid():
    password = generate_temporary_password()
    assert len(password) >= 8


@pytest.mark.django_db
def test_list_city_founders_requires_admin(api_client):
    response = api_client.get(LIST_URL)
    assert response.status_code in {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN}


@pytest.mark.django_db
@patch("apps.founders.views.send_city_founder_invite_email_task.delay")
def test_create_list_update_delete_city_founder(mock_delay, auth_client, admin_user, city):
    create_response = auth_client.post(
        LIST_URL,
        {
            "full_name": "Omar Founder",
            "email": "omar.founder@example.com",
            "city_id": str(city.id),
        },
        format="json",
    )
    assert create_response.status_code == status.HTTP_201_CREATED
    assert create_response.data["full_name"] == "Omar Founder"
    assert create_response.data["city_name"] == city.name
    assert create_response.data["country_code"] == city.country.code
    assert create_response.data["status"] == "pending_first_login"
    founder_id = create_response.data["id"]

    user = User.objects.get(email="omar.founder@example.com")
    assert user.role == User.Role.CITY_FOUNDER
    assert user.must_change_password is True
    assert user.is_identity_verified is True
    assert user.is_staff is False
    assert user.is_superuser is False
    assert user.groups.count() == 0
    assert user.user_permissions.count() == 0
    assert Founder.objects.filter(
        pk=founder_id,
        city_id=city.id,
        status=Founder.Status.PENDING_FIRST_LOGIN,
    ).exists()
    mock_delay.assert_called_once()
    assert AdminAuditLog.objects.filter(action=AdminAuditLog.Action.CITY_FOUNDER_CREATE).exists()

    list_response = auth_client.get(LIST_URL)
    assert list_response.status_code == status.HTTP_200_OK
    assert len(list_response.data) == 1

    update_response = auth_client.patch(
        reverse("city-founder-detail", kwargs={"founder_id": founder_id}),
        {"full_name": "Omar Updated", "status": "inactive"},
        format="json",
    )
    assert update_response.status_code == status.HTTP_200_OK
    assert update_response.data["full_name"] == "Omar Updated"
    assert update_response.data["status"] == "inactive"

    bad_delete = auth_client.delete(
        reverse("city-founder-detail", kwargs={"founder_id": founder_id}),
        {"confirmation_name": "Wrong Name"},
        format="json",
    )
    assert bad_delete.status_code == status.HTTP_400_BAD_REQUEST
    assert User.objects.filter(email="omar.founder@example.com").exists()

    delete_response = auth_client.delete(
        reverse("city-founder-detail", kwargs={"founder_id": founder_id}),
        {"confirmation_name": "Omar Updated"},
        format="json",
    )
    assert delete_response.status_code == status.HTTP_204_NO_CONTENT
    assert not User.objects.filter(email="omar.founder@example.com").exists()
    assert not Founder.objects.filter(pk=founder_id).exists()
    assert AdminAuditLog.objects.filter(action=AdminAuditLog.Action.CITY_FOUNDER_DELETE).exists()


@pytest.mark.django_db
@patch("apps.founders.views.send_city_founder_invite_email_task.delay")
def test_cannot_create_second_active_founder_for_same_city(mock_delay, auth_client, city):
    auth_client.post(
        LIST_URL,
        {
            "full_name": "First Founder",
            "email": "first.founder@example.com",
            "city_id": str(city.id),
        },
        format="json",
    )
    second = auth_client.post(
        LIST_URL,
        {
            "full_name": "Second Founder",
            "email": "second.founder@example.com",
            "city_id": str(city.id),
        },
        format="json",
    )
    assert second.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_operational_location_endpoints(auth_client, city):
    countries = auth_client.get(reverse("operational-country-list"))
    assert countries.status_code == status.HTTP_200_OK
    assert any(item["id"] == str(city.country_id) for item in countries.data)

    cities = auth_client.get(
        reverse("operational-city-list"),
        {"country_id": str(city.country_id)},
    )
    assert cities.status_code == status.HTTP_200_OK
    assert any(item["id"] == str(city.id) for item in cities.data)

    missing = auth_client.get(
        reverse("operational-city-list"),
        {"country_id": str(uuid4())},
    )
    assert missing.status_code == status.HTTP_200_OK
    assert missing.data == []
