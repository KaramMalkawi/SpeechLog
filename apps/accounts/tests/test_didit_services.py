import uuid
from datetime import date, timedelta

import pytest
from django.utils import timezone

from apps.accounts.didit.services import apply_didit_status, _classify_resident_type
from apps.accounts.didit.verification import calculate_age, extract_id_document, validate_extracted_id_document
from apps.accounts.models import IdentityVerificationSession, User
from apps.accounts.names import display_name_from_official_full_name
from tests.factories import UserFactory


def _valid_id_verification(**overrides):
    today = timezone.now().date()
    payload = {
        "full_name": "Rami Saleem Emile Janini",
        "nationality": "JOR",
        "date_of_birth": (today - timedelta(days=365 * 25)).isoformat(),
        "expiration_date": (today + timedelta(days=365 * 5)).isoformat(),
        "gender": "M",
        "age": 25,
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
def test_expatriate_auto_verified_when_nationality_matches_residence():
    user = UserFactory(
        full_name="Jane Doe",
        residence_country_code="JO",
        verification_status=User.VerificationStatus.UNVERIFIED,
        registration_step=1,
    )
    session = IdentityVerificationSession.objects.create(
        user=user,
        provider_session_id=uuid.uuid4(),
        status="Not Started",
    )

    apply_didit_status(
        user=user,
        session=session,
        status="Approved",
        decision={"id_verifications": [_valid_id_verification(nationality="JOR")]},
    )
    user.refresh_from_db()

    assert user.resident_type == User.ResidentType.EXPATRIATE
    assert user.verification_status == User.VerificationStatus.VERIFIED
    assert user.registration_step == 2
    assert user.manual_verification_approved is True
    assert user.nationality_code == "JO"
    assert user.official_full_name == "Rami Saleem Emile Janini"
    assert user.full_name == "Rami Janini"


@pytest.mark.django_db
def test_local_requires_manual_verification_when_nationality_differs_from_residence():
    user = UserFactory(
        residence_country_code="JO",
        verification_status=User.VerificationStatus.UNVERIFIED,
        registration_step=1,
    )
    session = IdentityVerificationSession.objects.create(
        user=user,
        provider_session_id=uuid.uuid4(),
        status="In Progress",
    )

    apply_didit_status(
        user=user,
        session=session,
        status="Approved",
        decision={"id_verifications": [_valid_id_verification(nationality="FRA")]},
    )
    user.refresh_from_db()

    assert user.resident_type == User.ResidentType.LOCAL
    assert user.nationality_code == "FR"
    assert user.verification_status == User.VerificationStatus.PENDING_REVIEW
    assert user.registration_step == 3
    assert user.manual_verification_approved is False
    assert user.is_identity_verified is False


def test_classify_resident_type():
    assert _classify_resident_type(nationality_code="JO", residence_country_code="JO") == User.ResidentType.EXPATRIATE
    assert _classify_resident_type(nationality_code="FR", residence_country_code="JO") == User.ResidentType.LOCAL


def test_display_name_from_official_full_name():
    assert display_name_from_official_full_name("Rami Saleem Emile Janini") == "Rami Janini"
    assert display_name_from_official_full_name("Jane Doe") == "Jane Doe"
    assert display_name_from_official_full_name("Madonna") == "Madonna"
    assert display_name_from_official_full_name("  ") == ""


@pytest.mark.django_db
def test_apply_didit_status_rejects_under_minimum_age(settings):
    settings.MIN_REGISTRATION_AGE = 18
    user = UserFactory(verification_status=User.VerificationStatus.UNVERIFIED)
    session = IdentityVerificationSession.objects.create(
        user=user,
        provider_session_id=uuid.uuid4(),
        status="In Progress",
    )
    young_dob = (timezone.now().date() - timedelta(days=365 * 10)).isoformat()

    apply_didit_status(
        user=user,
        session=session,
        status="Approved",
        decision={"id_verifications": [_valid_id_verification(date_of_birth=young_dob, age=10)]},
    )
    user.refresh_from_db()

    assert user.verification_status == User.VerificationStatus.REJECTED


@pytest.mark.django_db
def test_apply_didit_status_rejects_expired_document():
    user = UserFactory(verification_status=User.VerificationStatus.UNVERIFIED)
    session = IdentityVerificationSession.objects.create(
        user=user,
        provider_session_id=uuid.uuid4(),
        status="In Progress",
    )
    expired = (timezone.now().date() - timedelta(days=30)).isoformat()

    apply_didit_status(
        user=user,
        session=session,
        status="Approved",
        decision={"id_verifications": [_valid_id_verification(expiration_date=expired)]},
    )
    user.refresh_from_db()

    assert user.verification_status == User.VerificationStatus.REJECTED


@pytest.mark.django_db
def test_in_progress_does_not_downgrade_pending_review():
    user = UserFactory(
        residence_country_code="JO",
        verification_status=User.VerificationStatus.PENDING_REVIEW,
        nationality_code="FR",
        official_full_name="Already Extracted",
    )
    session = IdentityVerificationSession.objects.create(
        user=user,
        provider_session_id=uuid.uuid4(),
        status="Approved",
    )

    apply_didit_status(
        user=user,
        session=session,
        status="In Progress",
        decision={"id_verifications": []},
    )
    user.refresh_from_db()

    assert user.verification_status == User.VerificationStatus.PENDING_REVIEW
    assert user.nationality_code == "FR"
    assert user.official_full_name == "Already Extracted"


@pytest.mark.django_db
def test_start_session_does_not_reset_pending_review(settings):
    settings.DIDIT_API_KEY = "test-key"
    settings.DIDIT_WORKFLOW_ID = "11111111-1111-1111-1111-111111111111"
    user = UserFactory(verification_status=User.VerificationStatus.PENDING_REVIEW)

    from unittest.mock import MagicMock, patch
    from apps.accounts.didit.services import start_didit_verification_session

    mock_response = {
        "session_id": str(uuid.uuid4()),
        "status": "Not Started",
        "url": "https://verification.didit.me/session/abc",
    }
    with patch("apps.accounts.didit.services.DiditClient") as client_cls:
        client_cls.return_value.create_session.return_value = mock_response
        start_didit_verification_session(
            user=user,
            callback_url="mixedmiles://identity-callback",
        )

    user.refresh_from_db()
    assert user.verification_status == User.VerificationStatus.PENDING_REVIEW


@pytest.mark.django_db
def test_validate_extracted_id_document_requires_dob_and_expiration():
    document = extract_id_document({"full_name": "Jane Doe", "nationality": "JOR"})
    is_valid, errors = validate_extracted_id_document(document)

    assert is_valid is False
    assert "missing_date_of_birth" in errors
    assert "missing_expiration_date" in errors


def test_calculate_age():
    today = date(2026, 7, 6)
    assert calculate_age(date_of_birth=date(2000, 7, 6), on_date=today) == 26
    assert calculate_age(date_of_birth=date(2000, 7, 7), on_date=today) == 25
