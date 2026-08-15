from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.accounts.onboarding import OnboardingStep, resolve_onboarding_step
from apps.accounts.services import mark_user_verified

REGISTER_URL = reverse("register")
LOGIN_URL = reverse("auth-login")
REGISTER_STATUS_URL = reverse("register-status")
PROFILE_ONBOARDING_COMPLETE_URL = reverse("me-profile-onboarding-complete")


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def registration_payload(request):
    suffix = request.node.name.replace("[", "_").replace("]", "_")[:40]
    return {
        "first_name": "Jane",
        "last_name": "Doe",
        "email": f"orch.{suffix}@example.com",
        "password": "Str0ngPass!",
    }


@pytest.mark.django_db
def test_resolve_onboarding_step_verify_email():
    user = User(
        email="a@example.com",
        email_verified=False,
        verification_status=User.VerificationStatus.UNVERIFIED,
    )
    assert resolve_onboarding_step(user) == OnboardingStep.VERIFY_EMAIL


@pytest.mark.django_db
def test_resolve_onboarding_step_complete_profile_after_email():
    user = User(
        email="a@example.com",
        email_verified=True,
        profile_onboarding_completed=False,
        verification_status=User.VerificationStatus.UNVERIFIED,
    )
    assert resolve_onboarding_step(user) == OnboardingStep.COMPLETE_PROFILE


@pytest.mark.django_db
def test_resolve_onboarding_step_home_after_profile_onboarding():
    user = User(
        email="a@example.com",
        email_verified=True,
        profile_onboarding_completed=True,
        verification_status=User.VerificationStatus.UNVERIFIED,
    )
    assert resolve_onboarding_step(user) == OnboardingStep.HOME


@pytest.mark.django_db
def test_resolve_onboarding_step_home_when_fully_verified():
    user = User(
        email="a@example.com",
        email_verified=True,
        profile_onboarding_completed=True,
        verification_status=User.VerificationStatus.VERIFIED,
        manual_verification_approved=True,
    )
    assert resolve_onboarding_step(user) == OnboardingStep.HOME


@pytest.mark.django_db
@patch("apps.accounts.tasks.send_email_verification_otp_task.delay")
def test_register_status_includes_next_step(mock_delay, api_client, registration_payload):
    register_response = api_client.post(REGISTER_URL, registration_payload, format="json")
    token = register_response.data["registration_token"]

    response = api_client.get(
        REGISTER_STATUS_URL,
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["next_step"] == OnboardingStep.VERIFY_EMAIL
    assert response.data["email_verified"] is False


@pytest.mark.django_db
@patch("apps.accounts.tasks.send_email_verification_otp_task.delay")
def test_login_unverified_email_returns_registration_token(
    mock_delay, api_client, registration_payload
):
    api_client.post(REGISTER_URL, registration_payload, format="json")

    response = api_client.post(
        LOGIN_URL,
        {
            "email": registration_payload["email"],
            "password": registration_payload["password"],
        },
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data["code"] == "email_verification_required"
    assert response.data["next_step"] == OnboardingStep.VERIFY_EMAIL
    assert response.data["email"] == registration_payload["email"]
    assert "registration_token" in response.data
    assert response.data["email_verified"] is False


@pytest.mark.django_db
@patch("apps.accounts.tasks.send_email_verification_otp_task.delay")
def test_login_email_verified_needs_profile_onboarding(
    mock_delay, api_client, registration_payload
):
    api_client.post(REGISTER_URL, registration_payload, format="json")
    user = User.objects.get(email=registration_payload["email"])
    user.email_verified = True
    user.profile_onboarding_completed = False
    user.save(update_fields=["email_verified", "profile_onboarding_completed"])

    response = api_client.post(
        LOGIN_URL,
        {
            "email": registration_payload["email"],
            "password": registration_payload["password"],
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data
    assert response.data["next_step"] == OnboardingStep.COMPLETE_PROFILE


@pytest.mark.django_db
@patch("apps.accounts.tasks.send_email_verification_otp_task.delay")
def test_complete_profile_onboarding_reaches_home(
    mock_delay, api_client, registration_payload
):
    api_client.post(REGISTER_URL, registration_payload, format="json")
    user = User.objects.get(email=registration_payload["email"])
    user.email_verified = True
    user.profile_onboarding_completed = False
    user.save(update_fields=["email_verified", "profile_onboarding_completed"])

    login = api_client.post(
        LOGIN_URL,
        {
            "email": registration_payload["email"],
            "password": registration_payload["password"],
        },
        format="json",
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    response = api_client.post(
        PROFILE_ONBOARDING_COMPLETE_URL,
        {
            "bio": "Hello",
            "location": "Amman",
            "phone_number": "+962790000000",
            "skipped": False,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["next_step"] == OnboardingStep.HOME
    assert response.data["profile_onboarding_completed"] is True
    user.refresh_from_db()
    assert user.bio == "Hello"
    assert user.location == "Amman"
    assert user.phone_number == "+962790000000"
    assert user.profile_onboarding_completed is True


@pytest.mark.django_db
@patch("apps.accounts.tasks.send_email_verification_otp_task.delay")
def test_skip_profile_onboarding_reaches_home(
    mock_delay, api_client, registration_payload
):
    api_client.post(REGISTER_URL, registration_payload, format="json")
    user = User.objects.get(email=registration_payload["email"])
    user.email_verified = True
    user.save(update_fields=["email_verified"])

    login = api_client.post(
        LOGIN_URL,
        {
            "email": registration_payload["email"],
            "password": registration_payload["password"],
        },
        format="json",
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    response = api_client.post(
        PROFILE_ONBOARDING_COMPLETE_URL,
        {"skipped": True},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["next_step"] == OnboardingStep.HOME
    user.refresh_from_db()
    assert user.profile_onboarding_completed is True


@pytest.mark.django_db
@patch("apps.accounts.tasks.send_email_verification_otp_task.delay")
def test_login_verified_user_returns_tokens_and_home_step(
    mock_delay, api_client, registration_payload
):
    api_client.post(REGISTER_URL, registration_payload, format="json")
    user = User.objects.get(email=registration_payload["email"])
    mark_user_verified(user)
    user.profile_onboarding_completed = True
    user.save(update_fields=["profile_onboarding_completed"])

    response = api_client.post(
        LOGIN_URL,
        {
            "email": registration_payload["email"],
            "password": registration_payload["password"],
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data
    assert "refresh" in response.data
    assert response.data["full_name"] == user.full_name
    assert response.data["next_step"] == OnboardingStep.HOME
