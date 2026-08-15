import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.accounts.services import authenticate_admin_user
from apps.adminpanel.models import AdminAuditLog
from tests.factories import UserFactory

ADMIN_LOGIN_URL = reverse("auth-admin-login")
LOGIN_URL = reverse("auth-login")


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    user = UserFactory(
        email="admin@example.com",
        full_name="Platform Admin",
        admin=True,
    )
    user.set_password("Str0ngPass!")
    user.save(update_fields=["password"])
    return user


@pytest.fixture
def member_user(db):
    user = UserFactory(
        email="member@example.com",
        full_name="Regular Member",
        member=True,
    )
    user.set_password("Str0ngPass!")
    user.save(update_fields=["password"])
    return user


@pytest.fixture
def superuser(db):
    # Superuser without platform admin role — still allowed into the dashboard.
    user = UserFactory(
        email="super@example.com",
        full_name="Django Superuser",
        role=User.Role.NON_MEMBER,
        is_staff=True,
        is_superuser=True,
        verification_status=User.VerificationStatus.UNVERIFIED,
        registration_step=0,
    )
    user.set_password("Str0ngPass!")
    user.save(update_fields=["password"])
    return user


@pytest.mark.django_db
def test_authenticate_admin_user_accepts_admin(admin_user):
    user = authenticate_admin_user(
        email="admin@example.com",
        password="Str0ngPass!",
    )

    assert user == admin_user


@pytest.mark.django_db
def test_authenticate_admin_user_accepts_superuser(superuser):
    user = authenticate_admin_user(
        email="super@example.com",
        password="Str0ngPass!",
    )

    assert user == superuser
    assert user.is_superuser is True
    assert user.is_platform_admin is False


@pytest.mark.django_db
def test_authenticate_admin_user_rejects_non_admin(member_user):
    with pytest.raises(AuthenticationFailed, match="Only administrators"):
        authenticate_admin_user(
            email="member@example.com",
            password="Str0ngPass!",
        )


@pytest.mark.django_db
def test_admin_can_login_via_admin_endpoint(api_client, admin_user):
    response = api_client.post(
        ADMIN_LOGIN_URL,
        {"email": "admin@example.com", "password": "Str0ngPass!"},
        format="json",
        HTTP_USER_AGENT="pytest-agent",
    )

    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data
    assert "refresh" in response.data
    assert response.data["role"] == User.Role.ADMIN
    assert response.data["is_superuser"] is False
    assert response.data["email"] == "admin@example.com"
    audit_log = AdminAuditLog.objects.get(actor=admin_user)
    assert audit_log.action == AdminAuditLog.Action.ADMIN_LOGIN
    assert audit_log.metadata["user_agent"] == "pytest-agent"


@pytest.mark.django_db
def test_superuser_can_login_via_admin_endpoint(api_client, superuser):
    response = api_client.post(
        ADMIN_LOGIN_URL,
        {"email": "super@example.com", "password": "Str0ngPass!"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["is_superuser"] is True
    assert response.data["role"] == User.Role.NON_MEMBER
    assert AdminAuditLog.objects.filter(actor=superuser).exists()


@pytest.mark.django_db
def test_non_admin_cannot_login_via_admin_endpoint(api_client, member_user):
    response = api_client.post(
        ADMIN_LOGIN_URL,
        {"email": "member@example.com", "password": "Str0ngPass!"},
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "administrator" in str(response.data["detail"]).lower()
    assert AdminAuditLog.objects.count() == 0


@pytest.mark.django_db
def test_non_admin_can_still_use_general_login(api_client, member_user):
    response = api_client.post(
        LOGIN_URL,
        {"email": "member@example.com", "password": "Str0ngPass!"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["role"] == User.Role.MEMBER


@pytest.mark.django_db
def test_admin_login_rejects_bad_password(api_client, admin_user):
    response = api_client.post(
        ADMIN_LOGIN_URL,
        {"email": "admin@example.com", "password": "wrong-password"},
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert AdminAuditLog.objects.count() == 0


@pytest.mark.django_db
def test_admin_audit_log_is_immutable(api_client, admin_user):
    api_client.post(
        ADMIN_LOGIN_URL,
        {"email": "admin@example.com", "password": "Str0ngPass!"},
        format="json",
    )
    audit_log = AdminAuditLog.objects.get(actor=admin_user)

    audit_log.action = "admin.changed"
    with pytest.raises(ValueError, match="immutable"):
        audit_log.save()

    with pytest.raises(ValueError, match="immutable"):
        audit_log.delete()
