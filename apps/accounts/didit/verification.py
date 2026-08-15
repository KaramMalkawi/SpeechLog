from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from django.conf import settings
from django.utils import timezone

from apps.tenancy.country_data import alpha3_to_alpha2


@dataclass(frozen=True, slots=True)
class ExtractedIdDocument:
    official_full_name: str
    nationality: str
    date_of_birth: date | None
    expiration_date: date | None
    gender: str
    age: int | None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def extract_id_document(id_verification: dict) -> ExtractedIdDocument:
    age_value = id_verification.get("age")
    age = int(age_value) if age_value is not None and str(age_value).isdigit() else None
    gender = str(id_verification.get("gender") or "").strip().upper()[:8]

    full_name = str(id_verification.get("full_name") or "").strip()
    if not full_name:
        parts = [
            str(id_verification.get("first_name") or "").strip(),
            str(id_verification.get("last_name") or "").strip(),
        ]
        full_name = " ".join(part for part in parts if part)

    nationality = str(id_verification.get("nationality") or "").strip()
    if not nationality:
        # Some documents only expose issuing country.
        nationality = str(id_verification.get("issuing_state") or "").strip()

    return ExtractedIdDocument(
        official_full_name=full_name,
        nationality=nationality,
        date_of_birth=_parse_date(id_verification.get("date_of_birth")),
        expiration_date=_parse_date(
            id_verification.get("expiration_date") or id_verification.get("expiry_date")
        ),
        gender=gender,
        age=age,
    )


def calculate_age(*, date_of_birth: date, on_date: date | None = None) -> int:
    today = on_date or timezone.now().date()
    years = today.year - date_of_birth.year
    if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
        years -= 1
    return years


def validate_extracted_id_document(document: ExtractedIdDocument) -> tuple[bool, list[str]]:
    errors: list[str] = []
    min_age = settings.MIN_REGISTRATION_AGE
    today = timezone.now().date()

    if not document.nationality or alpha3_to_alpha2(document.nationality) is None:
        errors.append("missing_nationality")

    if document.date_of_birth is None:
        errors.append("missing_date_of_birth")
    elif calculate_age(date_of_birth=document.date_of_birth, on_date=today) < min_age:
        errors.append("under_minimum_age")

    if document.expiration_date is None:
        errors.append("missing_expiration_date")
    elif document.expiration_date < today:
        errors.append("document_expired")

    return not errors, errors
