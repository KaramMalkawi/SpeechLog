from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.accounts.services import (
    _issue_password_reset_token,
    build_password_reset_url,
    confirm_password_reset,
    request_password_reset,
)
from apps.accounts.services import mark_user_verified

PASSWORD_RESET_URL = reverse("auth-password-reset")
PASSWORD_RESET_CONFIRM_URL = reverse("auth-password-reset-confirm")
LOGIN_URL = reverse("auth-login")


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def verified_user(db):
    user = User.objects.create_user(
        email="jane@example.com",
        password="Str0ngPass!",
        full_name="Jane Doe",
    )
    mark_user_verified(user)
    return user


@pytest.mark.django_db
@patch("apps.accounts.tasks.send_password_reset_email_task.delay")
def test_password_reset_request_returns_generic_response_for_unknown_email(mock_delay, api_client):
    response = api_client.post(
        PASSWORD_RESET_URL,
        {"email": "missing@example.com"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert "If an account exists" in response.data["detail"]
    mock_delay.assert_not_called()


@pytest.mark.django_db
@patch("apps.accounts.tasks.send_password_reset_email_task.delay")
def test_password_reset_request_sends_email_for_active_user(mock_delay, api_client, verified_user):
    response = api_client.post(
        PASSWORD_RESET_URL,
        {"email": verified_user.email},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    mock_delay.assert_called_once()
    kwargs = mock_delay.call_args.kwargs
    assert kwargs["to"] == verified_user.email
    assert kwargs["reset_url"].startswith("https://mixedmiles.com/reset-password?token=")


@pytest.mark.django_db
@patch("apps.accounts.tasks.send_password_reset_email_task.delay")
def test_password_reset_request_same_response_for_existing_and_missing_email(
    mock_delay,
    api_client,
    verified_user,
):
    known = api_client.post(
        PASSWORD_RESET_URL,
        {"email": verified_user.email},
        format="json",
    )
    unknown = api_client.post(
        PASSWORD_RESET_URL,
        {"email": "missing@example.com"},
        format="json",
    )

    assert known.data["detail"] == unknown.data["detail"]


@pytest.mark.django_db
@patch("apps.accounts.tasks.send_password_reset_email_task.delay")
def test_password_reset_request_rate_limited(mock_delay, api_client, verified_user, settings):
    settings.PASSWORD_RESET_EMAIL_RATE_LIMIT = 2

    for _ in range(2):
        response = api_client.post(
            PASSWORD_RESET_URL,
            {"email": verified_user.email},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

    response = api_client.post(
        PASSWORD_RESET_URL,
        {"email": verified_user.email},
        format="json",
    )

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert response.data["code"] == "password_reset_rate_limited"
    assert mock_delay.call_count == 2


@pytest.mark.django_db
def test_password_reset_confirm_sets_new_password(verified_user):
    token = _issue_password_reset_token(verified_user)

    confirm_password_reset(token=token, new_password="NewStr0ngPass!")

    verified_user.refresh_from_db()
    assert verified_user.check_password("NewStr0ngPass!")


@pytest.mark.django_db
def test_password_reset_token_is_single_use(verified_user):
    token = _issue_password_reset_token(verified_user)
    confirm_password_reset(token=token, new_password="NewStr0ngPass!")

    with pytest.raises(Exception):
        confirm_password_reset(token=token, new_password="AnotherStr0ngPass!")


@pytest.mark.django_db
def test_password_reset_confirm_invalid_token(api_client):
    response = api_client.post(
        PASSWORD_RESET_CONFIRM_URL,
        {"token": "invalid-token", "new_password": "NewStr0ngPass!"},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "invalid_password_reset_token"


@pytest.mark.django_db
def test_password_reset_confirm_weak_password(api_client, verified_user):
    token = _issue_password_reset_token(verified_user)

    response = api_client.post(
        PASSWORD_RESET_CONFIRM_URL,
        {"token": token, "new_password": "123"},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "new_password" in response.data


@pytest.mark.django_db
def test_password_reset_confirm_allows_login_with_new_password(api_client, verified_user):
    token = _issue_password_reset_token(verified_user)
    api_client.post(
        PASSWORD_RESET_CONFIRM_URL,
        {"token": token, "new_password": "NewStr0ngPass!"},
        format="json",
    )

    response = api_client.post(
        LOGIN_URL,
        {"email": verified_user.email, "password": "NewStr0ngPass!"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data


@pytest.mark.django_db
def test_build_password_reset_url_uses_frontend_setting(settings):
    settings.PASSWORD_RESET_FRONTEND_URL = "https://app.mixedmiles.com/reset"
    url = build_password_reset_url("abc123")
    assert url == "https://app.mixedmiles.com/reset?token=abc123"
