"""City Founder application sync + review (Google Sheets → DB cache)."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.founders.models import FounderApplication, FounderApplicationSyncState
from apps.founders.sheets import (
    GoogleSheetsConfigError,
    open_founder_applications_spreadsheet,
)

logger = logging.getLogger(__name__)

UTC = ZoneInfo("UTC")

TIMESTAMP_KEYS = (
    "timestamp",
    "submitted",
    "submitted at",
    "submitted on",
    "submission time",
)
EMAIL_KEYS = ("email address", "email", "e-mail", "e mail")
COUNTRY_KEYS = (
    "country",
    "country name",
    "which country",
    "your country",
    "residence country",
    "city / country",
    "city/country",
)
NAME_KEYS = (
    "full name",
    "name",
    "your name",
    "applicant name",
    "full name (first and last)",
)


class FounderApplicationNotFound(Exception):
    """Raised when an application id does not exist."""


class FounderApplicationSyncError(Exception):
    """Raised when a Sheets sync fails."""


def _normalize_header(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def _pick_field(row: dict[str, Any], candidates: tuple[str, ...]) -> str:
    normalized = {_normalize_header(k): v for k, v in row.items()}
    for key in candidates:
        if key in normalized and normalized[key] not in (None, ""):
            return str(normalized[key]).strip()
    # Partial contains match (e.g. "Which country are you applying for?")
    for header, value in normalized.items():
        if value in (None, ""):
            continue
        for key in candidates:
            if key in header:
                return str(value).strip()
    return ""


def _parse_submitted_at(raw: str) -> datetime | None:
    if not raw:
        return None
    text = raw.strip()
    parsed = parse_datetime(text)
    if parsed is not None:
        if timezone.is_naive(parsed):
            return timezone.make_aware(parsed, UTC)
        return parsed.astimezone(UTC)

    for fmt in (
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%Y-%m-%d",
    ):
        try:
            naive = datetime.strptime(text, fmt)
            return timezone.make_aware(naive, UTC)
        except ValueError:
            continue
    return None


def _uniquify_headers(headers: list[str]) -> list[str]:
    """Make duplicate Google Form headers unique (gspread rejects duplicates)."""
    seen: dict[str, int] = {}
    unique: list[str] = []
    for raw in headers:
        header = (raw or "").strip() or "Untitled"
        count = seen.get(header, 0)
        seen[header] = count + 1
        unique.append(header if count == 0 else f"{header} ({count + 1})")
    return unique


def worksheet_records(worksheet) -> list[dict[str, Any]]:
    """Read all data rows as dicts, tolerating duplicate header names."""
    values = worksheet.get_all_values()
    if not values:
        return []
    headers = _uniquify_headers([str(cell) for cell in values[0]])
    records: list[dict[str, Any]] = []
    for row in values[1:]:
        if not any(str(cell).strip() for cell in row):
            continue
        padded = list(row) + [""] * max(0, len(headers) - len(row))
        records.append(
            {headers[i]: padded[i] for i in range(len(headers))}
        )
    return records


def _answers_payload(row: dict[str, Any]) -> dict[str, str]:
    return {
        str(key): "" if value is None else str(value)
        for key, value in row.items()
    }


def sheet_row_url(*, spreadsheet_id: str, sheet_gid: str, sheet_row: int) -> str:
    if not spreadsheet_id:
        return ""
    gid = sheet_gid or "0"
    return (
        f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
        f"#gid={gid}&range=A{sheet_row}"
    )


def get_or_create_sync_state() -> FounderApplicationSyncState:
    state, _ = FounderApplicationSyncState.objects.get_or_create(pk=1)
    return state


def founder_application_to_payload(application: FounderApplication) -> dict:
    return {
        "id": application.id,
        "sheet_row": application.sheet_row,
        "submitted_at": application.submitted_at,
        "email": application.email,
        "country_name": application.country_name,
        "full_name": application.full_name,
        "status": application.status,
        "answers": application.answers or {},
        "sheet_url": sheet_row_url(
            spreadsheet_id=application.spreadsheet_id,
            sheet_gid=application.sheet_gid,
            sheet_row=application.sheet_row,
        ),
        "created_at": application.created_at,
        "updated_at": application.updated_at,
    }


def sync_state_to_payload(state: FounderApplicationSyncState) -> dict:
    return {
        "last_synced_at": state.last_synced_at,
        "last_sync_error": state.last_sync_error,
        "last_sync_row_count": state.last_sync_row_count,
        "spreadsheet_id": state.spreadsheet_id,
        "spreadsheet_url": state.spreadsheet_url,
    }


@transaction.atomic
def sync_founder_applications_from_sheet() -> dict:
    """Pull form responses from Google Sheets into the local DB cache.

    Existing review statuses are preserved. New rows default to under_review.
    Call sparingly (scheduled twice daily + manual refresh) to respect quotas.
    """
    state = get_or_create_sync_state()
    try:
        spreadsheet = open_founder_applications_spreadsheet()
        worksheet = spreadsheet.sheet1
        records = worksheet_records(worksheet)
    except GoogleSheetsConfigError as exc:
        state.last_sync_error = str(exc)
        state.save(update_fields=["last_sync_error", "updated_at"])
        raise FounderApplicationSyncError(str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — surface Sheets/network errors to admin
        message = f"Google Sheets sync failed: {exc}"
        logger.exception(message)
        state.last_sync_error = message
        state.save(update_fields=["last_sync_error", "updated_at"])
        raise FounderApplicationSyncError(message) from exc

    spreadsheet_id = spreadsheet.id
    sheet_gid = str(worksheet.id)
    spreadsheet_url = spreadsheet.url

    seen_rows: set[int] = set()
    created = 0
    updated = 0

    for index, row in enumerate(records):
        # Sheet row 1 = headers; first data row is 2.
        sheet_row = index + 2
        seen_rows.add(sheet_row)
        answers = _answers_payload(row)
        email = _pick_field(row, EMAIL_KEYS)
        country_name = _pick_field(row, COUNTRY_KEYS)
        full_name = _pick_field(row, NAME_KEYS)
        submitted_at = _parse_submitted_at(_pick_field(row, TIMESTAMP_KEYS))

        existing = FounderApplication.objects.filter(sheet_row=sheet_row).first()
        if existing is None:
            FounderApplication.objects.create(
                sheet_row=sheet_row,
                submitted_at=submitted_at,
                email=email,
                country_name=country_name,
                full_name=full_name,
                answers=answers,
                status=FounderApplication.Status.UNDER_REVIEW,
                spreadsheet_id=spreadsheet_id,
                sheet_gid=sheet_gid,
            )
            created += 1
            continue

        existing.submitted_at = submitted_at
        existing.email = email
        existing.country_name = country_name
        existing.full_name = full_name
        existing.answers = answers
        existing.spreadsheet_id = spreadsheet_id
        existing.sheet_gid = sheet_gid
        existing.save(
            update_fields=[
                "submitted_at",
                "email",
                "country_name",
                "full_name",
                "answers",
                "spreadsheet_id",
                "sheet_gid",
                "updated_at",
            ]
        )
        updated += 1

    # Rows removed from the sheet are left in DB with their status (audit trail).
    state.last_synced_at = timezone.now()
    state.last_sync_error = ""
    state.last_sync_row_count = len(seen_rows)
    state.spreadsheet_id = spreadsheet_id
    state.spreadsheet_url = spreadsheet_url
    state.save(
        update_fields=[
            "last_synced_at",
            "last_sync_error",
            "last_sync_row_count",
            "spreadsheet_id",
            "spreadsheet_url",
            "updated_at",
        ]
    )

    return {
        "created": created,
        "updated": updated,
        "total": len(seen_rows),
        "last_synced_at": state.last_synced_at,
        "spreadsheet_url": spreadsheet_url,
    }


@transaction.atomic
def update_founder_application_status(
    *,
    application_id: UUID,
    status: str,
) -> FounderApplication:
    if status not in FounderApplication.Status.values:
        raise ValueError(f"Invalid status: {status}")

    application = FounderApplication.objects.filter(pk=application_id).first()
    if application is None:
        raise FounderApplicationNotFound()

    if application.status == status:
        return application

    application.status = status
    application.save(update_fields=["status", "updated_at"])
    return application
