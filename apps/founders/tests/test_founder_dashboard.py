from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.founders.models import Founder
from tests.factories import CityFactory, CountryFactory, UserFactory

DASHBOARD_LOGIN_URL = reverse("auth-dashboard-login")
OVERVIEW_URL = reverse("founder-dashboard-overview")
CHANGE_PASSWORD_URL = reverse("founder-change-password")
CITY_FOUNDERS_URL = reverse("city-founder-list")


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def city(db):
    return CityFactory(country=CountryFactory())


@pytest.fixture
def city_founder_user(db, city):
    user = UserFactory(
        email="founder.dash@example.com",
        full_name="Founder Dash",
        city_founder=True,
        verification_status=User.VerificationStatus.VERIFIED,
        registration_step=2,
        manual_verification_approved=True,
    )
    user.set_password("Str0ngPass!")
    user.must_change_password = True
    user.save(update_fields=["password", "must_change_password"])
    Founder.objects.create(
        user=user,
        city_id=city.id,
        status=Founder.Status.PENDING_FIRST_LOGIN,
    )
    return user


@pytest.fixture
def member_user(db):
    user = UserFactory(email="member.dash@example.com", member=True)
    user.set_password("Str0ngPass!")
    user.save(update_fields=["password"])
    return user


@pytest.fixture
def admin_user(db):
    user = UserFactory(email="admin.dash@example.com", admin=True)
    user.set_password("Str0ngPass!")
    user.save(update_fields=["password"])
    return user


@pytest.mark.django_db
def test_dashboard_login_accepts_city_founder_and_activates(api_client, city_founder_user, city):
    response = api_client.post(
        DASHBOARD_LOGIN_URL,
        {"email": "founder.dash@example.com", "password": "Str0ngPass!"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["role"] == User.Role.CITY_FOUNDER
    assert response.data["full_name"] == "Founder Dash"
    assert response.data["must_change_password"] is True
    assert "access" in response.data

    founder = Founder.objects.get(user=city_founder_user)
    assert founder.status == Founder.Status.ACTIVE


@pytest.mark.django_db
def test_founder_overview_blocked_until_password_changed(api_client, city_founder_user):
    token = RefreshToken.for_user(city_founder_user).access_token
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = api_client.get(OVERVIEW_URL)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_founder_change_password_clears_flag(api_client, city_founder_user, city):
    Founder.objects.filter(user=city_founder_user).update(status=Founder.Status.ACTIVE)
    token = RefreshToken.for_user(city_founder_user).access_token
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = api_client.post(
        CHANGE_PASSWORD_URL,
        {
            "current_password": "Str0ngPass!",
            "new_password": "NewStr0ngPass!",
        },
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["welcome_message"] == "Welcome, Founder Dash"
    assert response.data["status"] == Founder.Status.ACTIVE

    city_founder_user.refresh_from_db()
    assert city_founder_user.must_change_password is False
    assert city_founder_user.check_password("NewStr0ngPass!")

    overview = api_client.get(OVERVIEW_URL)
    assert overview.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_dashboard_login_rejects_member(api_client, member_user):
    response = api_client.post(
        DASHBOARD_LOGIN_URL,
        {"email": "member.dash@example.com", "password": "Str0ngPass!"},
        format="json",
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_dashboard_login_rejects_suspended_founder(api_client, city_founder_user):
    Founder.objects.filter(user=city_founder_user).update(status=Founder.Status.SUSPENDED)
    response = api_client.post(
        DASHBOARD_LOGIN_URL,
        {"email": "founder.dash@example.com", "password": "Str0ngPass!"},
        format="json",
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_founder_overview_requires_city_founder_role(api_client, member_user):
    token = RefreshToken.for_user(member_user).access_token
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = api_client.get(OVERVIEW_URL)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_founder_overview_returns_welcome(api_client, city_founder_user, city):
    city_founder_user.must_change_password = False
    city_founder_user.save(update_fields=["must_change_password"])
    Founder.objects.filter(user=city_founder_user).update(status=Founder.Status.ACTIVE)
    token = RefreshToken.for_user(city_founder_user).access_token
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = api_client.get(OVERVIEW_URL)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["welcome_message"] == "Welcome, Founder Dash"
    assert response.data["city_name"] == city.name
    assert response.data["full_name"] == "Founder Dash"


@pytest.mark.django_db
def test_city_founder_cannot_list_city_founders(api_client, city_founder_user):
    city_founder_user.must_change_password = False
    city_founder_user.save(update_fields=["must_change_password"])
    Founder.objects.filter(user=city_founder_user).update(status=Founder.Status.ACTIVE)
    token = RefreshToken.for_user(city_founder_user).access_token
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = api_client.get(CITY_FOUNDERS_URL)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_dashboard_login_accepts_admin(api_client, admin_user):
    response = api_client.post(
        DASHBOARD_LOGIN_URL,
        {"email": "admin.dash@example.com", "password": "Str0ngPass!"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["role"] == User.Role.ADMIN
