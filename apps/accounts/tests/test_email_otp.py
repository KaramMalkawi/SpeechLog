from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.accounts.services import (
    issue_email_verification_otp,
    verify_email_otp,
)

REGISTER_URL = reverse("register")
VERIFY_EMAIL_URL = reverse("register-verify-email")
RESEND_OTP_URL = reverse("register-resend-email-otp")


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def registration_payload():
    return {
        "first_name": "Jane",
        "last_name": "Doe",
        "email": "jane.otp@example.com",
        "password": "Str0ngPass!",
    }


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
@patch("apps.accounts.tasks.send_email_verification_otp_task.delay")
def test_register_queues_email_otp(mock_delay, api_client, registration_payload):
    response = api_client.post(REGISTER_URL, registration_payload, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["email_verified"] is False
    assert "registration_token" in response.data
    mock_delay.assert_called_once()
    assert mock_delay.call_args.kwargs["to"] == "jane.otp@example.com"
    assert len(mock_delay.call_args.kwargs["otp"]) == 6

    user = User.objects.get(email="jane.otp@example.com")
    assert user.email_verified is False


@pytest.mark.django_db
@patch("apps.accounts.tasks.send_email_verification_otp_task.delay")
def test_verify_email_otp_success(mock_delay, api_client, registration_payload):
    register_response = api_client.post(REGISTER_URL, registration_payload, format="json")
    token = register_response.data["registration_token"]
    otp = mock_delay.call_args.kwargs["otp"]

    response = api_client.post(
        VERIFY_EMAIL_URL,
        {"otp": otp},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["email_verified"] is True
    user = User.objects.get(email="jane.otp@example.com")
    assert user.email_verified is True

    # After email OTP the next step is soft profile setup (skippable).
    # Access tokens are issued immediately so photo upload / details work.
    assert response.data["next_step"] == "complete_profile"
    assert "access" in response.data
    assert "refresh" in response.data


@pytest.mark.django_db
@patch("apps.accounts.tasks.send_email_verification_otp_task.delay")
def test_verify_email_otp_assigns_default_community(
    mock_delay, api_client, registration_payload
):
    from tests.factories import CommunityFactory

    community = CommunityFactory(slug="amman-expats")
    register_response = api_client.post(REGISTER_URL, registration_payload, format="json")
    token = register_response.data["registration_token"]
    otp = mock_delay.call_args.kwargs["otp"]

    response = api_client.post(
        VERIFY_EMAIL_URL,
        {"otp": otp},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == status.HTTP_200_OK
    user = User.objects.get(email="jane.otp@example.com")
    assert user.active_community_id == community.id
    assert user.memberships.filter(community_id=community.id).exists()


@pytest.mark.django_db
@patch("apps.accounts.tasks.send_email_verification_otp_task.delay")
def test_verify_email_otp_rejects_wrong_code(mock_delay, api_client, registration_payload):
    register_response = api_client.post(REGISTER_URL, registration_payload, format="json")
    token = register_response.data["registration_token"]

    response = api_client.post(
        VERIFY_EMAIL_URL,
        {"otp": "000000"},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    user = User.objects.get(email="jane.otp@example.com")
    assert user.email_verified is False


@pytest.mark.django_db
def test_otp_is_stored_hashed_not_plaintext():
    user = User.objects.create_user(
        email="hash.check@example.com",
        password="Str0ngPass!",
        full_name="Hash Check",
    )
    otp = issue_email_verification_otp(user=user)
    payload = cache.get(f"email_otp:{user.pk}")

    assert payload is not None
    assert otp not in str(payload)
    assert payload["digest"].startswith("argon2")


@pytest.mark.django_db
@patch("apps.accounts.tasks.send_email_verification_otp_task.delay")
def test_resend_email_otp(mock_delay, api_client, registration_payload):
    register_response = api_client.post(REGISTER_URL, registration_payload, format="json")
    token = register_response.data["registration_token"]
    mock_delay.reset_mock()

    response = api_client.post(
        RESEND_OTP_URL,
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == status.HTTP_200_OK
    mock_delay.assert_called_once()


@pytest.mark.django_db
def test_verify_email_otp_service_marks_verified():
    user = User.objects.create_user(
        email="verify.service@example.com",
        password="Str0ngPass!",
        full_name="Verify Service",
    )
    otp = issue_email_verification_otp(user=user)
    verified = verify_email_otp(user=user, otp=otp)
    assert verified.email_verified is True
