"""Google Sheets client for City Founder application responses."""

from __future__ import annotations

from functools import lru_cache

import gspread
from django.conf import settings
from google.oauth2.service_account import Credentials

SCOPES = (
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
)


class GoogleSheetsConfigError(Exception):
    """Raised when Google service-account settings are incomplete."""


def google_service_account_info() -> dict:
    private_key = (settings.GOOGLE_SA_PRIVATE_KEY or "").replace("\\n", "\n")
    required = {
        "project_id": settings.GOOGLE_SA_PROJECT_ID,
        "private_key_id": settings.GOOGLE_SA_PRIVATE_KEY_ID,
        "private_key": private_key,
        "client_email": settings.GOOGLE_SA_CLIENT_EMAIL,
        "client_id": settings.GOOGLE_SA_CLIENT_ID,
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise GoogleSheetsConfigError(
            "Google Sheets is not configured. Missing: " + ", ".join(missing)
        )
    return {
        "type": "service_account",
        "project_id": required["project_id"],
        "private_key_id": required["private_key_id"],
        "private_key": required["private_key"],
        "client_email": required["client_email"],
        "client_id": required["client_id"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "universe_domain": "googleapis.com",
    }


@lru_cache(maxsize=1)
def get_gspread_client() -> gspread.Client:
    info = google_service_account_info()
    credentials = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(credentials)


def open_founder_applications_spreadsheet() -> gspread.Spreadsheet:
    """Open the responses spreadsheet by ID (preferred) or by title."""
    client = get_gspread_client()
    sheet_id = (settings.FOUNDER_APPLICATIONS_SHEET_ID or "").strip()
    share_hint = (
        f"Share the spreadsheet with {settings.GOOGLE_SA_CLIENT_EMAIL} "
        "(Viewer is enough to sync; Editor if you later write status back)."
    )
    if sheet_id:
        try:
            return client.open_by_key(sheet_id)
        except PermissionError as exc:
            raise GoogleSheetsConfigError(
                "Google Sheets returned 403 (no permission). " + share_hint
            ) from exc
        except gspread.exceptions.APIError as exc:
            raise GoogleSheetsConfigError(
                f"Could not open spreadsheet {sheet_id}: {exc}. " + share_hint
            ) from exc

    name = (settings.FOUNDER_APPLICATIONS_SHEET_NAME or "").strip()
    if not name:
        raise GoogleSheetsConfigError(
            "Set FOUNDER_APPLICATIONS_SHEET_ID (preferred) or "
            "FOUNDER_APPLICATIONS_SHEET_NAME."
        )
    try:
        return client.open(name)
    except gspread.exceptions.APIError as exc:
        raise GoogleSheetsConfigError(
            "Could not open the sheet by name. Enable the Google Drive API for "
            "this project, or set FOUNDER_APPLICATIONS_SHEET_ID from the "
            "spreadsheet URL (/d/<ID>/edit). " + share_hint
        ) from exc
    except PermissionError as exc:
        raise GoogleSheetsConfigError(
            "Google Sheets returned 403 (no permission). " + share_hint
        ) from exc


def clear_gspread_client_cache() -> None:
    get_gspread_client.cache_clear()
