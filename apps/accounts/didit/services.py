from __future__ import annotations

import logging
from uuid import UUID

from django.conf import settings
from django.db import IntegrityError, transaction

from apps.accounts.didit.client import DiditClient, DiditError
from apps.accounts.didit.verification import (
    calculate_age,
    extract_id_document,
    validate_extracted_id_document,
)
from apps.accounts.models import DiditWebhookDelivery, IdentityVerificationSession, User
from apps.accounts.names import display_name_from_official_full_name
from apps.tenancy.country_data import alpha3_to_alpha2

logger = logging.getLogger(__name__)

SESSION_WEBHOOK_TYPES = frozenset({"status.updated", "data.updated"})


def _extract_id_verification(decision: dict) -> dict:
    items = decision.get("id_verifications") or []
    return items[0] if items else {}


def _normalize_gender(value: str) -> str:
    normalized = value.strip().upper()
    if normalized in {User.Gender.MALE, "MALE", "MAN"}:
        return User.Gender.MALE
    if normalized in {User.Gender.FEMALE, "FEMALE", "WOMAN"}:
        return User.Gender.FEMALE
    return ""


def _apply_extracted_document_to_session(
    *,
    session: IdentityVerificationSession,
    document,
) -> None:
    session.extracted_full_name = document.official_full_name
    session.extracted_nationality = document.nationality
    session.extracted_date_of_birth = document.date_of_birth
    session.extracted_expiration_date = document.expiration_date
    session.extracted_gender = document.gender


def _apply_identity_fields_from_document(*, user: User, document) -> str | None:
    """Persist OCR fields; return ISO alpha-2 nationality code when present."""
    if document.official_full_name:
        user.official_full_name = document.official_full_name
        # Public display name = first + last from the official ID name.
        user.full_name = display_name_from_official_full_name(document.official_full_name)
    nationality_code = alpha3_to_alpha2(document.nationality)
    if nationality_code:
        user.nationality_code = nationality_code
    if document.date_of_birth:
        user.date_of_birth = document.date_of_birth
        user.age = document.age if document.age is not None else calculate_age(date_of_birth=document.date_of_birth)
    if document.expiration_date:
        user.document_expiration_date = document.expiration_date
    gender = _normalize_gender(document.gender)
    if gender:
        user.gender = gender
    return nationality_code


def _classify_resident_type(*, nationality_code: str, residence_country_code: str) -> str:
    if nationality_code.upper() == residence_country_code.upper():
        return User.ResidentType.EXPATRIATE
    return User.ResidentType.LOCAL


def _finalize_verification_after_id_checks(*, user: User, nationality_code: str) -> None:
    if not user.residence_country_code:
        user.verification_status = User.VerificationStatus.PENDING_REVIEW
        user.registration_step = 3
        return

    user.resident_type = _classify_resident_type(
        nationality_code=nationality_code,
        residence_country_code=user.residence_country_code,
    )
    if user.resident_type == User.ResidentType.EXPATRIATE:
        user.verification_status = User.VerificationStatus.VERIFIED
        user.registration_step = 2
        user.manual_verification_approved = True
    else:
        user.verification_status = User.VerificationStatus.PENDING_REVIEW
        user.registration_step = 3
        user.manual_verification_approved = False


@transaction.atomic
def start_didit_verification_session(*, user: User, callback_url: str) -> IdentityVerificationSession:
    if not settings.DIDIT_API_KEY or not settings.DIDIT_WORKFLOW_ID:
        raise DiditError("Didit is not configured. Set DIDIT_API_KEY and DIDIT_WORKFLOW_ID.")

    client = DiditClient()
    response = client.create_session(
        workflow_id=settings.DIDIT_WORKFLOW_ID,
        vendor_data=str(user.id),
        callback=callback_url,
        metadata={"email": user.email},
    )

    session, _created = IdentityVerificationSession.objects.update_or_create(
        provider_session_id=UUID(response["session_id"]),
        defaults={
            "user": user,
            "status": response.get("status", "Not Started"),
            "verification_url": response.get("url", ""),
        },
    )
    # Never clobber pending_review / verified when opening a new Didit session.
    # Only clear an explicit rejection so the user can retry from a clean state.
    if user.verification_status == User.VerificationStatus.REJECTED:
        user.verification_status = User.VerificationStatus.UNVERIFIED
        user.save(update_fields=["verification_status", "updated_at"])
    return session


def _normalize_didit_status(status: str) -> str:
    return str(status or "").strip()


def apply_didit_status(*, user: User, session: IdentityVerificationSession, status: str, decision: dict) -> User:
    status = _normalize_didit_status(status)
    session.status = status
    session.decision_payload = decision

    id_verification = _extract_id_verification(decision)
    document = extract_id_document(id_verification)
    _apply_extracted_document_to_session(session=session, document=document)
    session.save()

    protected_statuses = {
        User.VerificationStatus.VERIFIED,
        User.VerificationStatus.PENDING_REVIEW,
    }

    if status == "Approved":
        is_valid, errors = validate_extracted_id_document(document)
        if is_valid:
            nationality_code = _apply_identity_fields_from_document(user=user, document=document)
            if nationality_code:
                _finalize_verification_after_id_checks(user=user, nationality_code=nationality_code)
            else:
                user.verification_status = User.VerificationStatus.PENDING_REVIEW
                user.registration_step = 3
        else:
            logger.info(
                "Didit approved but identity checks failed user_id=%s errors=%s",
                user.id,
                errors,
            )
            # Keep OCR fields on the session; only reject when not already past review.
            if user.verification_status not in protected_statuses:
                user.verification_status = User.VerificationStatus.REJECTED
    elif status == "Declined":
        if user.verification_status != User.VerificationStatus.VERIFIED:
            user.verification_status = User.VerificationStatus.REJECTED
    elif status == "In Review":
        # Persist OCR when present so admin review has the extracted identity.
        if document.official_full_name or document.nationality or document.date_of_birth:
            _apply_identity_fields_from_document(user=user, document=document)
        if user.verification_status != User.VerificationStatus.VERIFIED:
            user.verification_status = User.VerificationStatus.PENDING_REVIEW
            user.registration_step = 3
    elif status in {"In Progress", "Not Started", "Resubmitted", "Awaiting User"}:
        # In-flight Didit sessions must not wipe pending_review / verified.
        pass
    elif status in {"Abandoned", "Expired", "Kyc Expired", "KYC Expired"}:
        # Same: don't downgrade users already in review or verified.
        if user.verification_status == User.VerificationStatus.UNVERIFIED:
            pass

    user.save()
    return user


def _fetch_decision_from_api(session_id: str) -> dict:
    client = DiditClient()
    return client.get_session_decision(session_id)


@transaction.atomic
def process_didit_webhook(
    *,
    event_id: UUID,
    payload: dict,
    verification_method: str = "v2",
) -> None:
    webhook_type = payload.get("webhook_type", "")

    try:
        DiditWebhookDelivery.objects.create(
            event_id=event_id,
            webhook_type=webhook_type,
        )
    except IntegrityError:
        return

    if webhook_type not in SESSION_WEBHOOK_TYPES:
        logger.info(
            "Ignoring unsupported Didit webhook_type=%s event_id=%s",
            webhook_type,
            event_id,
        )
        return

    session_id = payload.get("session_id")
    vendor_data = payload.get("vendor_data")
    status = payload.get("status")
    if not session_id or not vendor_data or not status:
        logger.warning(
            "Didit session webhook missing required fields event_id=%s webhook_type=%s",
            event_id,
            webhook_type,
        )
        return

    try:
        user = User.objects.get(pk=vendor_data)
    except (User.DoesNotExist, ValueError):
        logger.warning("Didit webhook vendor_data user not found: %s", vendor_data)
        return

    session, _ = IdentityVerificationSession.objects.get_or_create(
        provider_session_id=UUID(session_id),
        defaults={"user": user},
    )
    session.last_event_id = event_id
    session.save(update_fields=["last_event_id", "updated_at"])

    decision = payload.get("decision") or {}
    if verification_method == "simple" or not decision:
        if settings.DIDIT_API_KEY:
            try:
                decision = _fetch_decision_from_api(str(session_id))
                status = decision.get("status", status)
            except DiditError:
                logger.exception("Failed to re-fetch Didit decision for session %s", session_id)
                return

    apply_didit_status(user=user, session=session, status=status, decision=decision)


def refresh_user_verification_from_didit(user: User) -> IdentityVerificationSession | None:
    session = (
        IdentityVerificationSession.objects.filter(user=user)
        .order_by("-created_at")
        .first()
    )
    if session is None or not settings.DIDIT_API_KEY:
        return None

    client = DiditClient()
    try:
        decision_payload = client.get_session_decision(str(session.provider_session_id))
    except DiditError:
        return session

    status = decision_payload.get("status", session.status)
    apply_didit_status(user=user, session=session, status=status, decision=decision_payload)
    return session
