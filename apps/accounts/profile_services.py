from __future__ import annotations

import mimetypes
import uuid
from datetime import date
from pathlib import PurePosixPath

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.profile_selectors import (
    get_membership_display_id,
    get_membership_display_name,
    get_membership_status,
    get_profile_photo_url,
)
from core.storage import (
    S3StorageError,
    delete_object,
    generate_presigned_upload_url,
    get_object_metadata,
    is_s3_configured,
)


def _add_one_year(day: date) -> date:
    try:
        return day.replace(year=day.year + 1)
    except ValueError:
        # Feb 29 → Feb 28 next year
        return day.replace(year=day.year + 1, day=28)


def _add_one_month(day: date) -> date:
    if day.month == 12:
        year, month = day.year + 1, 1
    else:
        year, month = day.year, day.month + 1
    # Clamp day for shorter months (e.g. Jan 31 → Feb 28).
    for candidate in (day.day, 30, 29, 28):
        try:
            return date(year, month, candidate)
        except ValueError:
            continue
    return date(year, month, 1)


@transaction.atomic
def activate_annual_membership(*, user: User, plan: str = "annual") -> dict:
    """Activate paid Member after simulated checkout (until Milestone 4 gateway).

    Idempotent: Non-Members upgrade to Member; other roles are left unchanged.
    ``plan`` is ``monthly`` or ``annual`` (default).
    """
    from apps.accounts.services import apply_user_role

    normalized = (plan or "annual").strip().lower()
    if normalized not in {"monthly", "annual"}:
        normalized = "annual"

    if user.role == User.Role.NON_MEMBER:
        user = apply_user_role(user, User.Role.MEMBER)

    today = timezone.now().date()
    if normalized == "monthly":
        next_billing = _add_one_month(today)
        return {
            "plan": "Monthly Plan",
            "plan_id": "monthly",
            "plan_title": "Mixed Miles — Monthly Plan",
            "amount_cents": 900,
            "currency": "USD",
            "next_billing_date": next_billing.isoformat(),
            "membership_status": get_membership_status(user),
            "role": user.role,
            "membership_id": get_membership_display_id(user=user),
            "membership_display_name": get_membership_display_name(user=user)
            or user.full_name
            or "",
        }

    next_billing = _add_one_year(today)
    return {
        "plan": "Annual Plan",
        "plan_id": "annual",
        "plan_title": "Mixed Miles — Annual Plan",
        "amount_cents": 7900,
        "currency": "USD",
        "next_billing_date": next_billing.isoformat(),
        "membership_status": get_membership_status(user),
        "role": user.role,
        "membership_id": get_membership_display_id(user=user),
        "membership_display_name": get_membership_display_name(user=user)
        or user.full_name
        or "",
    }


class ProfilePhotoError(Exception):
    """Raised when profile photo operations fail."""


class ProfileUpdateError(Exception):
    """Raised when a profile field update is not allowed."""


def is_display_name_locked(*, user: User) -> bool:
    """Display name is frozen once identity OCR has produced an official name."""
    return bool((user.official_full_name or "").strip())


_CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def _extension_for_content_type(content_type: str) -> str:
    normalized = content_type.lower().split(";")[0].strip()
    extension = _CONTENT_TYPE_EXTENSIONS.get(normalized)
    if extension:
        return extension
    guessed = mimetypes.guess_extension(normalized)
    return guessed or ".bin"


def _profile_key_for_user(user_id: uuid.UUID, content_type: str) -> str:
    extension = _extension_for_content_type(content_type)
    return f"{settings.PROFILE_PHOTO_KEY_PREFIX}/{user_id}/{uuid.uuid4()}{extension}"


def _validate_profile_object_key(*, user_id: uuid.UUID, object_key: str) -> None:
    prefix = f"{settings.PROFILE_PHOTO_KEY_PREFIX}/{user_id}/"
    if not object_key.startswith(prefix):
        raise ProfilePhotoError("Invalid profile photo key.")
    if PurePosixPath(object_key).name in {"", ".", ".."}:
        raise ProfilePhotoError("Invalid profile photo key.")


@transaction.atomic
def update_profile_bio(*, user: User, bio: str) -> User:
    user.bio = bio.strip()
    user.save(update_fields=["bio", "updated_at"])
    return user


@transaction.atomic
def update_profile_details(
    *,
    user: User,
    full_name: str | None = None,
    bio: str | None = None,
    location: str | None = None,
    phone_number: str | None = None,
) -> User:
    """Partial update for profile fields collected during onboarding / edit profile."""
    update_fields: list[str] = []
    if full_name is not None:
        if is_display_name_locked(user=user):
            raise ProfileUpdateError(
                "Display name is locked after identity verification."
            )
        user.full_name = full_name.strip()[:160]
        update_fields.append("full_name")
    if bio is not None:
        user.bio = bio.strip()[:500]
        update_fields.append("bio")
    if location is not None:
        user.location = location.strip()[:160]
        update_fields.append("location")
    if phone_number is not None:
        user.phone_number = phone_number.strip()[:32]
        update_fields.append("phone_number")
    if update_fields:
        update_fields.append("updated_at")
        user.save(update_fields=update_fields)
    return user


@transaction.atomic
def complete_profile_onboarding(*, user: User) -> User:
    """Mark post-OTP profile setup as done (finished or skipped)."""
    if user.profile_onboarding_completed:
        return user
    user.profile_onboarding_completed = True
    user.save(update_fields=["profile_onboarding_completed", "updated_at"])
    return user


def create_profile_photo_upload(
    *,
    user: User,
    content_type: str,
    content_length: int,
) -> dict:
    if not is_s3_configured():
        raise ProfilePhotoError("File uploads are not configured.")

    normalized_type = content_type.lower().split(";")[0].strip()
    if normalized_type not in settings.PROFILE_PHOTO_ALLOWED_CONTENT_TYPES:
        raise ProfilePhotoError("Unsupported image type.")

    if content_length <= 0 or content_length > settings.PROFILE_PHOTO_MAX_BYTES:
        raise ProfilePhotoError("Image file is too large.")

    object_key = _profile_key_for_user(user.id, normalized_type)
    try:
        presigned = generate_presigned_upload_url(
            object_key=object_key,
            content_type=normalized_type,
            content_length=content_length,
        )
    except S3StorageError as exc:
        raise ProfilePhotoError("Could not create upload URL.") from exc

    return presigned


@transaction.atomic
def confirm_profile_photo_upload(*, user: User, object_key: str) -> User:
    _validate_profile_object_key(user_id=user.id, object_key=object_key)

    try:
        metadata = get_object_metadata(object_key)
    except S3StorageError as exc:
        raise ProfilePhotoError("Could not verify uploaded file.") from exc

    if metadata is None:
        raise ProfilePhotoError("Uploaded file was not found.")

    content_type = metadata["content_type"].lower().split(";")[0].strip()
    if content_type not in settings.PROFILE_PHOTO_ALLOWED_CONTENT_TYPES:
        raise ProfilePhotoError("Unsupported image type.")

    if metadata["content_length"] > settings.PROFILE_PHOTO_MAX_BYTES:
        raise ProfilePhotoError("Image file is too large.")

    previous_key = user.profile_photo_key
    user.profile_photo_key = object_key
    user.save(update_fields=["profile_photo_key", "updated_at"])

    if previous_key and previous_key != object_key:
        try:
            delete_object(previous_key)
        except S3StorageError:
            pass

    return user


@transaction.atomic
def remove_profile_photo(*, user: User) -> User:
    previous_key = user.profile_photo_key
    user.profile_photo_key = ""
    user.save(update_fields=["profile_photo_key", "updated_at"])

    if previous_key:
        try:
            delete_object(previous_key)
        except S3StorageError as exc:
            raise ProfilePhotoError("Could not delete profile photo.") from exc

    return user


def build_profile_payload(*, user: User, viewer: User | None = None) -> dict:
    from apps.accounts.onboarding import resolve_onboarding_step

    is_own_profile = viewer is not None and viewer.pk == user.pk
    is_following = bool(getattr(user, "is_following", False))

    payload = {
        "user_id": user.id,
        "full_name": user.full_name,
        "bio": user.bio,
        "location": user.location,
        "phone_number": user.phone_number,
        "photo_url": get_profile_photo_url(user),
        "role": user.role,
        "followers_count": getattr(user, "followers_count", 0),
        "following_count": getattr(user, "following_count", 0),
        "membership_status": get_membership_status(user),
        "active_community_id": user.active_community_id,
        "is_following": is_following,
        "is_own_profile": is_own_profile,
        "profile_onboarding_completed": user.profile_onboarding_completed,
    }
    if is_own_profile:
        from apps.tenancy.country_data import get_country_by_code

        nationality = (
            get_country_by_code(user.nationality_code) if user.nationality_code else None
        )
        payload["email"] = user.email
        payload["is_identity_verified"] = user.is_identity_verified
        payload["verification_status"] = user.verification_status
        payload["official_full_name"] = user.official_full_name or ""
        payload["display_name_locked"] = is_display_name_locked(user=user)
        payload["nationality_code"] = user.nationality_code or ""
        payload["nationality_name"] = nationality.name if nationality else ""
        payload["next_step"] = resolve_onboarding_step(user)
        payload["membership_id"] = get_membership_display_id(user=user)
        payload["membership_display_name"] = (
            get_membership_display_name(user=user) or user.full_name or ""
        )
    return payload
