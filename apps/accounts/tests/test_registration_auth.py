import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from unittest.mock import patch

from apps.accounts.models import User
from apps.accounts.services import mark_user_verified

REGISTER_URL = reverse("register")
LOGIN_URL = reverse("auth-login")
REGISTER_STATUS_URL = reverse("register-status")
ME_URL = reverse("me")


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def registration_payload():
    return {
        "first_name": "Jane",
        "last_name": "Doe",
        "email": "jane@example.com",
        "password": "Str0ngPass!",
    }


@pytest.mark.django_db
@patch("apps.accounts.tasks.send_email_verification_otp_task.delay")
def test_register_creates_unverified_user(mock_delay, api_client, registration_payload):
    response = api_client.post(REGISTER_URL, registration_payload, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["verification_status"] == User.VerificationStatus.UNVERIFIED
    assert response.data["email_verified"] is False
    assert response.data["registration_step"] == 1
    assert "registration_token" in response.data
    mock_delay.assert_called_once()

    user = User.objects.get(email="jane@example.com")
    assert user.full_name == "Jane Doe"
    assert user.nationality_code == ""
    assert user.residence_country_code == ""
    assert user.phone_number == ""
    assert user.email_verified is False
    assert user.role == User.Role.NON_MEMBER
    assert user.is_identity_verified is False


@pytest.mark.django_db
@patch("apps.accounts.tasks.send_email_verification_otp_task.delay")
def test_register_rejects_blank_first_name(mock_delay, api_client, registration_payload):
    registration_payload["first_name"] = "   "

    response = api_client.post(REGISTER_URL, registration_payload, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "first_name" in response.data
    mock_delay.assert_not_called()


@pytest.mark.django_db
@patch("apps.accounts.tasks.send_email_verification_otp_task.delay")
def test_unverified_user_cannot_login(mock_delay, api_client, registration_payload):
    api_client.post(REGISTER_URL, registration_payload, format="json")

    response = api_client.post(
        LOGIN_URL,
        {"email": "jane@example.com", "password": "Str0ngPass!"},
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data["code"] == "email_verification_required"
    assert "verification" in str(response.data["detail"]).lower()


@pytest.mark.django_db
@patch("apps.accounts.tasks.send_email_verification_otp_task.delay")
def test_local_verified_without_admin_approval_can_still_login(
    mock_delay, api_client, registration_payload
):
    """Manual admin approval (like Didit identity verification) is currently
    optional — only email verification gates login."""
    api_client.post(REGISTER_URL, registration_payload, format="json")
    user = User.objects.get(email="jane@example.com")
    user.resident_type = User.ResidentType.LOCAL
    user.verification_status = User.VerificationStatus.VERIFIED
    user.email_verified = True
    user.registration_step = 2
    user.manual_verification_approved = False
    user.save()

    response = api_client.post(
        LOGIN_URL,
        {"email": "jane@example.com", "password": "Str0ngPass!"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data


@pytest.mark.django_db
@patch("apps.accounts.tasks.send_email_verification_otp_task.delay")
def test_verified_user_can_login(mock_delay, api_client, registration_payload):
    api_client.post(REGISTER_URL, registration_payload, format="json")
    user = User.objects.get(email="jane@example.com")
    mark_user_verified(user)

    response = api_client.post(
        LOGIN_URL,
        {"email": "jane@example.com", "password": "Str0ngPass!"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data
    assert "refresh" in response.data


@pytest.mark.django_db
@patch("apps.accounts.tasks.send_email_verification_otp_task.delay")
def test_registration_token_allows_status_endpoint(mock_delay, api_client, registration_payload):
    register_response = api_client.post(REGISTER_URL, registration_payload, format="json")
    token = register_response.data["registration_token"]

    response = api_client.get(
        REGISTER_STATUS_URL,
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["identity_verification_required"] is True
    assert response.data["email_verified"] is False


@pytest.mark.django_db
@patch("apps.accounts.tasks.send_email_verification_otp_task.delay")
def test_registration_token_cannot_access_protected_api(
    mock_delay, api_client, registration_payload
):
    register_response = api_client.post(REGISTER_URL, registration_payload, format="json")
    token = register_response.data["registration_token"]

    response = api_client.get(ME_URL, HTTP_AUTHORIZATION=f"Bearer {token}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
@patch("apps.accounts.tasks.send_email_verification_otp_task.delay")
def test_verified_user_can_access_me(mock_delay, api_client, registration_payload):
    api_client.post(REGISTER_URL, registration_payload, format="json")
    user = User.objects.get(email="jane@example.com")
    mark_user_verified(user)

    login_response = api_client.post(
        LOGIN_URL,
        {"email": "jane@example.com", "password": "Str0ngPass!"},
        format="json",
    )

    response = api_client.get(
        ME_URL,
        HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["email"] == "jane@example.com"


@pytest.mark.django_db
@patch("apps.accounts.tasks.send_email_verification_otp_task.delay")
def test_start_verification_requires_email_verified(
    mock_delay, api_client, registration_payload, settings
):
    settings.DIDIT_API_KEY = ""
    settings.DIDIT_WORKFLOW_ID = ""
    register_response = api_client.post(REGISTER_URL, registration_payload, format="json")
    token = register_response.data["registration_token"]

    response = api_client.post(
        reverse("register-verification"),
        {"callback_url": "http://localhost:8000/callback"},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data["code"] == "email_verification_required"


@pytest.mark.django_db
@patch("apps.accounts.tasks.send_email_verification_otp_task.delay")
def test_start_verification_requires_didit_config(
    mock_delay, api_client, registration_payload, settings
):
    settings.DIDIT_API_KEY = ""
    settings.DIDIT_WORKFLOW_ID = ""
    register_response = api_client.post(REGISTER_URL, registration_payload, format="json")
    token = register_response.data["registration_token"]
    user = User.objects.get(email="jane@example.com")
    user.email_verified = True
    user.save(update_fields=["email_verified"])

    response = api_client.post(
        reverse("register-verification"),
        {"callback_url": "http://localhost:8000/callback"},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == status.HTTP_502_BAD_GATEWAY
