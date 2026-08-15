from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import IdentityVerificationSession, User
from tests.factories import UserFactory

START_URL = reverse("me-identity-verify")
STATUS_URL = reverse("me-identity-status")


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def member(db):
    user = UserFactory(email="identity.member@example.com", full_name="Identity Member")
    user.email_verified = True
    user.verification_status = User.VerificationStatus.UNVERIFIED
    user.save(update_fields=["email_verified", "verification_status"])
    return user


def _auth(user):
    return f"Bearer {RefreshToken.for_user(user).access_token}"


@pytest.mark.django_db
def test_identity_status_unverified(api_client, member):
    response = api_client.get(STATUS_URL, HTTP_AUTHORIZATION=_auth(member))
    assert response.status_code == status.HTTP_200_OK
    assert response.data["is_identity_verified"] is False
    assert response.data["verification_status"] == User.VerificationStatus.UNVERIFIED
    assert response.data["full_name"] == "Identity Member"
    assert response.data["official_full_name"] == ""
    assert response.data["nationality_code"] == ""
    assert response.data["nationality_name"] == ""


@pytest.mark.django_db
def test_identity_status_verified_includes_name_and_nationality(api_client, member):
    member.verification_status = User.VerificationStatus.VERIFIED
    member.resident_type = User.ResidentType.EXPATRIATE
    member.official_full_name = "Jane Official"
    member.nationality_code = "JO"
    member.save(
        update_fields=[
            "verification_status",
            "resident_type",
            "official_full_name",
            "nationality_code",
        ]
    )

    response = api_client.get(STATUS_URL, HTTP_AUTHORIZATION=_auth(member))
    assert response.status_code == status.HTTP_200_OK
    assert response.data["is_identity_verified"] is True
    assert response.data["official_full_name"] == "Jane Official"
    assert response.data["nationality_code"] == "JO"
    assert response.data["nationality_name"] == "Jordan"


@pytest.mark.django_db
@patch("apps.accounts.profile_views.start_didit_verification_session")
def test_identity_start_returns_verification_url(mock_start, api_client, member):
    session = MagicMock()
    session.provider_session_id = "11111111-1111-1111-1111-111111111111"
    session.verification_url = "https://verification.didit.me/session/abc"
    session.status = "Not Started"
    mock_start.return_value = session

    response = api_client.post(
        START_URL,
        {"callback_url": "http://localhost:8000/callback"},
        format="json",
        HTTP_AUTHORIZATION=_auth(member),
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["verification_url"] == "https://verification.didit.me/session/abc"
    assert response.data["is_identity_verified"] is False
    mock_start.assert_called_once()


@pytest.mark.django_db
def test_identity_start_already_verified(api_client, member):
    member.verification_status = User.VerificationStatus.VERIFIED
    member.resident_type = User.ResidentType.EXPATRIATE
    member.save(update_fields=["verification_status", "resident_type"])

    response = api_client.post(
        START_URL,
        {"callback_url": "http://localhost:8000/callback"},
        format="json",
        HTTP_AUTHORIZATION=_auth(member),
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["is_identity_verified"] is True
