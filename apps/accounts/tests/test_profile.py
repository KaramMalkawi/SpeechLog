from __future__ import annotations

from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User, UserFollow
from apps.accounts.services import mark_user_verified
from tests.factories import UserFactory

MY_PROFILE_URL = reverse("me-profile")
PRESIGN_URL = reverse("me-profile-photo-presign")
CONFIRM_URL = reverse("me-profile-photo-confirm")
DELETE_PHOTO_URL = reverse("me-profile-photo-delete")


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def verified_user(db):
    user = User.objects.create_user(
        email="profile@example.com",
        password="Str0ngPass!",
        full_name="Profile User",
    )
    mark_user_verified(user)
    user.profile_onboarding_completed = True
    user.save(update_fields=["profile_onboarding_completed"])
    return user


@pytest.fixture
def auth_client(api_client, verified_user):
    api_client.force_authenticate(user=verified_user)
    return api_client


def user_profile_url(user_id):
    return reverse("user-profile", kwargs={"user_id": user_id})


@pytest.mark.django_db
def test_get_my_profile(auth_client, verified_user):
    verified_user.bio = "Community builder in Amman."
    verified_user.save(update_fields=["bio"])

    response = auth_client.get(MY_PROFILE_URL)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["user_id"] == verified_user.id
    assert response.data["full_name"] == verified_user.full_name
    assert response.data["bio"] == "Community builder in Amman."
    assert response.data["followers_count"] == 0
    assert response.data["following_count"] == 0
    assert response.data["membership_status"] == "inactive"
    assert response.data["is_own_profile"] is True
    assert response.data["is_following"] is False


@pytest.mark.django_db
def test_patch_my_profile_bio(auth_client, verified_user):
    response = auth_client.patch(MY_PROFILE_URL, {"bio": "  New bio  "}, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["bio"] == "New bio"
    verified_user.refresh_from_db()
    assert verified_user.bio == "New bio"


@pytest.mark.django_db
def test_patch_my_profile_full_name(auth_client, verified_user):
    response = auth_client.patch(
        MY_PROFILE_URL,
        {"full_name": "  Baraa Malkawi  ", "bio": "Hello from Amman"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["full_name"] == "Baraa Malkawi"
    assert response.data["bio"] == "Hello from Amman"
    verified_user.refresh_from_db()
    assert verified_user.full_name == "Baraa Malkawi"
    assert verified_user.bio == "Hello from Amman"


@pytest.mark.django_db
def test_patch_my_profile_full_name_locked_after_identity(auth_client, verified_user):
    verified_user.official_full_name = "Rami Saleem Emile Janini"
    verified_user.full_name = "Rami Janini"
    verified_user.save(update_fields=["official_full_name", "full_name", "updated_at"])

    response = auth_client.patch(
        MY_PROFILE_URL,
        {"full_name": "Someone Else"},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    verified_user.refresh_from_db()
    assert verified_user.full_name == "Rami Janini"

    # Bio updates still allowed when the display name is locked.
    bio_response = auth_client.patch(
        MY_PROFILE_URL,
        {"bio": "Still editable"},
        format="json",
    )
    assert bio_response.status_code == status.HTTP_200_OK
    assert bio_response.data["display_name_locked"] is True
    assert bio_response.data["full_name"] == "Rami Janini"


@pytest.mark.django_db
def test_my_profile_includes_membership_display_fields(auth_client, verified_user):
    verified_user.full_name = "Ali Karam"
    verified_user.save(update_fields=["full_name", "updated_at"])

    response = auth_client.get(MY_PROFILE_URL)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["membership_display_name"] == "Ali Karam"
    assert response.data["membership_id"].startswith("#")
    assert len(response.data["membership_id"]) == 6


@pytest.mark.django_db
def test_follower_and_following_counts(auth_client, verified_user):
    follower = UserFactory()
    following = UserFactory()
    UserFollow.objects.create(follower=follower, following=verified_user)
    UserFollow.objects.create(follower=verified_user, following=following)

    response = auth_client.get(MY_PROFILE_URL)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["followers_count"] == 1
    assert response.data["following_count"] == 1


@pytest.mark.django_db
def test_get_public_profile(auth_client, verified_user):
    viewer = UserFactory()
    UserFollow.objects.create(follower=viewer, following=verified_user)
    api_client = APIClient()
    api_client.force_authenticate(user=viewer)

    verified_user.bio = "Public bio"
    verified_user.save(update_fields=["bio"])

    response = api_client.get(user_profile_url(verified_user.id))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["bio"] == "Public bio"
    assert response.data["is_own_profile"] is False
    assert response.data["is_following"] is True


@pytest.mark.django_db
def test_get_unverified_user_profile_returns_404(auth_client):
    unverified = User.objects.create_user(
        email="pending@example.com",
        password="Str0ngPass!",
        full_name="Pending User",
    )

    response = auth_client.get(user_profile_url(unverified.id))

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
@patch("apps.accounts.profile_services.is_s3_configured", return_value=True)
@patch("apps.accounts.profile_services.generate_presigned_upload_url")
def test_profile_photo_presign(mock_presign, mock_configured, auth_client, settings):
    settings.AWS_STORAGE_BUCKET_NAME = "test-bucket"
    mock_presign.return_value = {
        "upload_url": "https://s3.example.com/upload",
        "object_key": "profile-photos/test/key.jpg",
        "expires_in": 900,
        "headers": {"Content-Type": "image/jpeg", "Content-Length": "1024"},
    }

    response = auth_client.post(
        PRESIGN_URL,
        {"content_type": "image/jpeg", "content_length": 1024},
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["upload_url"] == "https://s3.example.com/upload"
    mock_presign.assert_called_once()


@pytest.mark.django_db
def test_profile_photo_presign_rejects_unsupported_type(auth_client, settings):
    settings.AWS_S3_ACCESS_KEY_ID = "key"
    settings.AWS_S3_SECRET_ACCESS_KEY = "secret"
    settings.AWS_STORAGE_BUCKET_NAME = "bucket"

    response = auth_client.post(
        PRESIGN_URL,
        {"content_type": "application/pdf", "content_length": 1024},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
@patch("apps.accounts.profile_services.get_object_metadata")
@patch("apps.accounts.profile_services.delete_object")
def test_profile_photo_confirm(mock_delete, mock_metadata, auth_client, verified_user, settings):
    object_key = f"profile-photos/{verified_user.id}/photo.jpg"
    mock_metadata.return_value = {
        "content_length": 2048,
        "content_type": "image/jpeg",
    }

    response = auth_client.post(CONFIRM_URL, {"object_key": object_key}, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["photo_url"].endswith(object_key)
    verified_user.refresh_from_db()
    assert verified_user.profile_photo_key == object_key
    mock_delete.assert_not_called()


@pytest.mark.django_db
@patch("apps.accounts.profile_services.delete_object")
@patch("apps.accounts.profile_services.get_object_metadata")
def test_profile_photo_confirm_replaces_previous_photo(
    mock_metadata,
    mock_delete,
    auth_client,
    verified_user,
):
    verified_user.profile_photo_key = f"profile-photos/{verified_user.id}/old.jpg"
    verified_user.save(update_fields=["profile_photo_key"])

    new_key = f"profile-photos/{verified_user.id}/new.jpg"
    mock_metadata.return_value = {
        "content_length": 2048,
        "content_type": "image/jpeg",
    }

    response = auth_client.post(CONFIRM_URL, {"object_key": new_key}, format="json")

    assert response.status_code == status.HTTP_200_OK
    mock_delete.assert_called_once_with(f"profile-photos/{verified_user.id}/old.jpg")


@pytest.mark.django_db
def test_activate_annual_membership_upgrades_non_member(auth_client, verified_user):
    assert verified_user.role == User.Role.NON_MEMBER

    response = auth_client.post(
        reverse("me-membership-activate"),
        {"plan": "annual"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["membership_status"] == "active"
    assert response.data["role"] == User.Role.MEMBER
    assert response.data["plan"] == "Annual Plan"
    assert response.data["plan_id"] == "annual"
    assert response.data["amount_cents"] == 7900
    assert response.data["next_billing_date"]
    verified_user.refresh_from_db()
    assert verified_user.role == User.Role.MEMBER


@pytest.mark.django_db
def test_activate_monthly_membership(auth_client, verified_user):
    response = auth_client.post(
        reverse("me-membership-activate"),
        {"plan": "monthly"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["plan"] == "Monthly Plan"
    assert response.data["plan_id"] == "monthly"
    assert response.data["amount_cents"] == 900
    assert response.data["membership_status"] == "active"
    verified_user.refresh_from_db()
    assert verified_user.role == User.Role.MEMBER


@pytest.mark.django_db
def test_activate_annual_membership_idempotent_for_member(auth_client):
    member = UserFactory(member=True, email_verified=True)
    api_client = APIClient()
    api_client.force_authenticate(user=member)

    response = api_client.post(reverse("me-membership-activate"), format="json")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["membership_status"] == "active"
    assert response.data["role"] == User.Role.MEMBER
