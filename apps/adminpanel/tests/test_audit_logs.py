from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.adminpanel.models import AdminAuditLog
from apps.adminpanel.services import record_admin_audit_event
from tests.factories import UserFactory

LIST_URL = reverse("admin-audit-log-list")


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    user = UserFactory(email="admin.audit@example.com", full_name="Admin Audit", admin=True)
    user.set_password("Str0ngPass!")
    user.save(update_fields=["password"])
    return user


@pytest.fixture
def auth_client(api_client, admin_user):
    token = RefreshToken.for_user(admin_user).access_token
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api_client


@pytest.mark.django_db
def test_list_audit_logs_includes_admin_and_superadmin(auth_client, admin_user):
    superuser = UserFactory(
        email="super.audit@example.com",
        full_name="Super Audit",
        admin=True,
        is_superuser=True,
        is_staff=True,
    )
    member = UserFactory(email="member.audit@example.com", member=True)

    record_admin_audit_event(
        actor_id=admin_user.id,
        action=AdminAuditLog.Action.USER_DELETE,
        metadata={"email": "gone@example.com"},
    )
    record_admin_audit_event(
        actor_id=superuser.id,
        action=AdminAuditLog.Action.ADMIN_LOGIN,
        metadata={"email": superuser.email},
    )
    record_admin_audit_event(
        actor_id=member.id,
        action=AdminAuditLog.Action.ADMIN_LOGIN,
        metadata={"email": member.email},
    )

    response = auth_client.get(LIST_URL)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["results"]) == 2
    roles = {row["actor_role"] for row in response.data["results"]}
    assert roles == {"admin", "superadmin"}
    assert "actions" in response.data


@pytest.mark.django_db
def test_filter_audit_logs_by_actor_role(auth_client, admin_user):
    superuser = UserFactory(
        email="super.filter@example.com",
        admin=True,
        is_superuser=True,
        is_staff=True,
    )
    record_admin_audit_event(
        actor_id=admin_user.id,
        action=AdminAuditLog.Action.USER_ROLE_UPDATE,
        metadata={
            "email": "x@example.com",
            "previous_role": "member",
            "new_role": "admin",
        },
    )
    record_admin_audit_event(
        actor_id=superuser.id,
        action=AdminAuditLog.Action.ADMIN_LOGIN,
        metadata={},
    )

    response = auth_client.get(LIST_URL, {"actor_role": "superadmin"})
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["results"]) == 1
    assert response.data["results"][0]["actor_role"] == "superadmin"


@pytest.mark.django_db
def test_filter_audit_logs_by_action_and_search(auth_client, admin_user):
    record_admin_audit_event(
        actor_id=admin_user.id,
        action=AdminAuditLog.Action.CITY_FOUNDER_CREATE,
        metadata={"email": "founder@example.com", "full_name": "Founder One"},
    )
    record_admin_audit_event(
        actor_id=admin_user.id,
        action=AdminAuditLog.Action.USER_DELETE,
        metadata={"email": "other@example.com"},
    )

    response = auth_client.get(
        LIST_URL,
        {"action": AdminAuditLog.Action.CITY_FOUNDER_CREATE, "search": "founder@"},
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["results"]) == 1
    assert "founder@example.com" in response.data["results"][0]["summary"]


@pytest.mark.django_db
def test_member_cannot_list_audit_logs(api_client):
    member = UserFactory(email="member.noaudit@example.com", member=True)
    token = RefreshToken.for_user(member).access_token
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = api_client.get(LIST_URL)
    assert response.status_code == status.HTTP_403_FORBIDDEN
