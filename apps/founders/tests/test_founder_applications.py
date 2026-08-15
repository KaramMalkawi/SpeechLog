from __future__ import annotations

from datetime import datetime, timezone as dt_timezone
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.founders.applications import (
    sync_founder_applications_from_sheet,
    update_founder_application_status,
)
from apps.founders.models import FounderApplication, FounderApplicationSyncState
from tests.factories import UserFactory

LIST_URL = reverse("founder-application-list")
SYNC_URL = reverse("founder-application-sync")


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    user = UserFactory(email="admin.apps@example.com", full_name="Admin Apps", admin=True)
    user.set_password("Str0ngPass!")
    user.save(update_fields=["password"])
    return user


@pytest.fixture
def auth_client(api_client, admin_user):
    token = RefreshToken.for_user(admin_user).access_token
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api_client


def _fake_spreadsheet(records: list[dict]):
    # Simulate get_all_values() used by worksheet_records().
    headers = list(records[0].keys()) if records else []
    values = [headers] + [[row.get(h, "") for h in headers] for row in records]
    worksheet = MagicMock()
    worksheet.get_all_values.return_value = values
    worksheet.id = 0
    spreadsheet = MagicMock()
    spreadsheet.id = "sheet-id-abc"
    spreadsheet.url = "https://docs.google.com/spreadsheets/d/sheet-id-abc/edit"
    spreadsheet.sheet1 = worksheet
    return spreadsheet


@pytest.mark.django_db
def test_sync_upserts_rows_and_preserves_status():
    records = [
        {
            "Timestamp": "7/17/2026 10:00:00",
            "Email Address": "one@example.com",
            "Country": "Jordan",
            "Full Name": "One Person",
            "Why apply?": "Because",
        },
        {
            "Timestamp": "7/17/2026 11:00:00",
            "Email Address": "two@example.com",
            "Country": "Lebanon",
            "Full Name": "Two Person",
            "Why apply?": "Also",
        },
    ]
    with patch(
        "apps.founders.applications.open_founder_applications_spreadsheet",
        return_value=_fake_spreadsheet(records),
    ):
        result = sync_founder_applications_from_sheet()

    assert result["created"] == 2
    assert FounderApplication.objects.count() == 2
    first = FounderApplication.objects.get(sheet_row=2)
    assert first.email == "one@example.com"
    assert first.country_name == "Jordan"
    assert first.status == FounderApplication.Status.UNDER_REVIEW
    assert first.answers["Why apply?"] == "Because"

    update_founder_application_status(
        application_id=first.id,
        status=FounderApplication.Status.ACCEPTED,
    )

    records[0]["Country"] = "Jordan (updated)"
    with patch(
        "apps.founders.applications.open_founder_applications_spreadsheet",
        return_value=_fake_spreadsheet(records),
    ):
        sync_founder_applications_from_sheet()

    first.refresh_from_db()
    assert first.country_name == "Jordan (updated)"
    assert first.status == FounderApplication.Status.ACCEPTED
    state = FounderApplicationSyncState.objects.get(pk=1)
    assert state.last_sync_row_count == 2
    assert state.last_sync_error == ""


@pytest.mark.django_db
def test_sync_handles_duplicate_headers():
    headers = [
        "Timestamp",
        "Email Address",
        "Email Address",
        "If yes, briefly explain:",
        "If yes, briefly explain:",
        "Country",
    ]
    values = [
        headers,
        [
            "7/17/2026 10:00:00",
            "a@example.com",
            "alt@example.com",
            "first",
            "second",
            "Jordan",
        ],
    ]
    worksheet = MagicMock()
    worksheet.get_all_values.return_value = values
    worksheet.id = 0
    spreadsheet = MagicMock()
    spreadsheet.id = "sheet-id-abc"
    spreadsheet.url = "https://docs.google.com/spreadsheets/d/sheet-id-abc/edit"
    spreadsheet.sheet1 = worksheet

    with patch(
        "apps.founders.applications.open_founder_applications_spreadsheet",
        return_value=spreadsheet,
    ):
        result = sync_founder_applications_from_sheet()

    assert result["created"] == 1
    app = FounderApplication.objects.get(sheet_row=2)
    assert app.email == "a@example.com"
    assert app.country_name == "Jordan"
    assert app.answers["Email Address"] == "a@example.com"
    assert app.answers["Email Address (2)"] == "alt@example.com"
    assert app.answers["If yes, briefly explain:"] == "first"
    assert app.answers["If yes, briefly explain: (2)"] == "second"


@pytest.mark.django_db
def test_list_applications_from_db(auth_client):
    FounderApplication.objects.create(
        sheet_row=2,
        email="cached@example.com",
        country_name="Jordan",
        full_name="Cached User",
        submitted_at=timezone.now(),
        answers={"Email Address": "cached@example.com"},
        status=FounderApplication.Status.REVIEWED,
        spreadsheet_id="abc",
        sheet_gid="0",
    )
    response = auth_client.get(LIST_URL)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]["email"] == "cached@example.com"
    assert response.data[0]["status"] == "reviewed"
    assert "sheet_url" in response.data[0]


@pytest.mark.django_db
def test_patch_status(auth_client):
    app = FounderApplication.objects.create(
        sheet_row=3,
        email="status@example.com",
        country_name="Egypt",
        answers={},
    )
    response = auth_client.patch(
        reverse("founder-application-detail", kwargs={"application_id": app.id}),
        {"status": "rejected"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["status"] == "rejected"
    app.refresh_from_db()
    assert app.status == FounderApplication.Status.REJECTED


@pytest.mark.django_db
def test_manual_sync_endpoint(auth_client):
    records = [
        {
            "Timestamp": "7/17/2026 12:00:00",
            "Email Address": "sync@example.com",
            "Country": "UAE",
            "Full Name": "Sync Me",
        }
    ]
    with patch(
        "apps.founders.applications.open_founder_applications_spreadsheet",
        return_value=_fake_spreadsheet(records),
    ):
        response = auth_client.post(SYNC_URL)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["created"] == 1
    assert FounderApplication.objects.filter(email="sync@example.com").exists()


@pytest.mark.django_db
def test_member_cannot_list_applications(api_client):
    member = UserFactory(email="member.apps@example.com", member=True)
    token = RefreshToken.for_user(member).access_token
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = api_client.get(LIST_URL)
    assert response.status_code == status.HTTP_403_FORBIDDEN
