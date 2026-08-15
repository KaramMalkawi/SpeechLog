from __future__ import annotations

import logging
import mimetypes
import uuid
from pathlib import PurePosixPath
from typing import Any
from uuid import UUID

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.adminpanel.models import AdminAuditLog
from apps.adminpanel.services import record_admin_audit_event
from apps.gatherings.exceptions import (
    GatheringAlreadyJoined,
    GatheringAtCapacity,
    GatheringCancelled,
    GatheringCommunityRequired,
    GatheringCoverError,
    GatheringCreatorCannotJoin,
    GatheringDeletionNotPending,
    GatheringDeletionPending,
    GatheringEditForbidden,
    GatheringEligibilityError,
    GatheringIdentityRequired,
    GatheringNotFound,
)
from apps.gatherings.models import GATHERING_HARD_CAP, Gathering, GatheringAttendee
from apps.gatherings.selectors import get_create_eligibility, get_join_eligibility
from apps.tenancy.models import Community
from core.storage import (
    S3StorageError,
    delete_object,
    generate_presigned_upload_url,
    get_object_metadata,
    is_s3_configured,
)

logger = logging.getLogger(__name__)

_CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def resolve_community_for_request(*, request_community: Community | None, user: User) -> Community:
    if request_community is not None:
        return request_community
    if user.is_authenticated and user.active_community_id:
        community = (
            Community.objects.select_related("city")
            .filter(id=user.active_community_id, is_active=True)
            .first()
        )
        if community is not None:
            return community
    raise GatheringCommunityRequired("An active community context is required.")


def _assert_identity_verified(user: User) -> None:
    if user.is_platform_admin or user.is_superadmin:
        return
    if not user.is_identity_verified:
        raise GatheringIdentityRequired(
            "Verify your identity before joining a gathering."
        )


def _assert_can_create(user: User) -> None:
    eligibility = get_create_eligibility(user=user)
    if eligibility["can_create"]:
        return
    required = eligibility["events_required"]
    raise GatheringEligibilityError(
        f"You need to attend at least {required} event"
        f"{'s' if required != 1 else ''} before creating a Gathering."
    )


def _assert_can_join(user: User) -> None:
    eligibility = get_join_eligibility(user=user)
    if eligibility["can_create"]:
        return
    required = eligibility["events_required"]
    raise GatheringEligibilityError(
        f"You need to attend at least {required} event"
        f"{'s' if required != 1 else ''} before joining a Gathering."
    )


def create_gathering(
    *,
    creator: User,
    community: Community,
    title: str,
    description: str = "",
    area: str,
    exact_location: str = "",
    map_link: str = "",
    starts_at,
    ends_at=None,
    max_attendees: int = GATHERING_HARD_CAP,
    cover_image_key: str = "",
) -> Gathering:
    _assert_can_create(creator)
    if max_attendees < 2 or max_attendees > GATHERING_HARD_CAP:
        raise GatheringEditForbidden(f"max_attendees must be between 2 and {GATHERING_HARD_CAP}.")
    if cover_image_key:
        _assert_cover_object_ready(object_key=cover_image_key, uploader_id=creator.id)

    # Creator hosts the gathering and does not occupy an attendee seat.
    return Gathering.all_objects.create(
        creator=creator,
        community_id=community.id,
        city_id=community.city_id,
        title=title,
        description=description,
        area=area,
        exact_location=exact_location,
        map_link=map_link,
        cover_image_key=cover_image_key,
        starts_at=starts_at,
        ends_at=ends_at,
        max_attendees=max_attendees,
    )


def _assert_can_edit_gathering(*, gathering: Gathering, actor: User) -> None:
    if actor.is_platform_admin or actor.is_superadmin:
        return
    if gathering.creator_id != actor.id:
        raise GatheringEditForbidden("Only the creator can edit this gathering.")


def _assert_can_moderate_deletion(*, actor: User) -> None:
    if not (actor.is_platform_admin or actor.is_superadmin):
        raise GatheringEditForbidden("Only admins can approve gathering deletions.")


@transaction.atomic
def update_gathering(
    *, gathering_id: UUID, community_id: UUID, actor: User, **fields: Any
) -> Gathering:
    gathering = (
        Gathering.all_objects.select_for_update()
        .filter(pk=gathering_id, community_id=community_id)
        .first()
    )
    if gathering is None:
        raise GatheringNotFound("Gathering not found.")
    _assert_can_edit_gathering(gathering=gathering, actor=actor)
    if gathering.is_cancelled:
        raise GatheringCancelled("This gathering has been cancelled.")
    if gathering.deletion_status == Gathering.DeletionStatus.APPROVED:
        raise GatheringCancelled("This gathering has been deleted.")
    if gathering.deletion_status == Gathering.DeletionStatus.PENDING:
        raise GatheringDeletionPending(
            "This gathering has a pending deletion request and cannot be edited."
        )

    # Creators cannot force-cancel via patch; use the deletion-request flow.
    fields.pop("is_cancelled", None)
    fields.pop("deletion_status", None)
    fields.pop("deletion_reason", None)

    if "max_attendees" in fields:
        value = fields["max_attendees"]
        if value is not None and (value < 2 or value > GATHERING_HARD_CAP):
            raise GatheringEditForbidden(
                f"max_attendees must be between 2 and {GATHERING_HARD_CAP}."
            )
        active_count = GatheringAttendee.all_objects.filter(
            gathering=gathering, is_active=True
        ).count()
        if value is not None and value < active_count:
            raise GatheringEditForbidden(
                f"max_attendees cannot be lower than current attendees ({active_count})."
            )

    if "cover_image_key" in fields and fields["cover_image_key"]:
        _assert_cover_object_ready(
            object_key=fields["cover_image_key"],
            uploader_id=gathering.creator_id,
        )

    previous_cover = gathering.cover_image_key
    for key, value in fields.items():
        if hasattr(gathering, key):
            setattr(gathering, key, value)
    gathering.save()

    if (
        "cover_image_key" in fields
        and previous_cover
        and previous_cover != gathering.cover_image_key
    ):
        try:
            delete_object(previous_cover)
        except S3StorageError:
            logger.exception("Failed to delete previous gathering cover key=%s", previous_cover)

    return gathering


@transaction.atomic
def request_gathering_deletion(
    *,
    gathering_id: UUID,
    community_id: UUID,
    actor: User,
    reason: str,
) -> Gathering:
    """Creator requests deletion; admins must approve before it is cancelled."""
    gathering = (
        Gathering.all_objects.select_for_update()
        .filter(pk=gathering_id, community_id=community_id)
        .first()
    )
    if gathering is None:
        raise GatheringNotFound("Gathering not found.")
    _assert_can_edit_gathering(gathering=gathering, actor=actor)
    if gathering.is_cancelled:
        raise GatheringCancelled("This gathering has already been cancelled.")
    if gathering.deletion_status == Gathering.DeletionStatus.APPROVED:
        raise GatheringCancelled("This gathering deletion was already approved.")

    cleaned = (reason or "").strip()
    if len(cleaned) < 3:
        raise GatheringEditForbidden("A deletion reason is required (at least 3 characters).")
    if len(cleaned) > 2000:
        raise GatheringEditForbidden("Deletion reason is too long.")

    if gathering.deletion_status == Gathering.DeletionStatus.PENDING:
        raise GatheringDeletionPending("A deletion request is already pending admin review.")

    gathering.deletion_status = Gathering.DeletionStatus.PENDING
    gathering.deletion_reason = cleaned
    gathering.deletion_requested_at = timezone.now()
    gathering.deletion_reviewed_at = None
    gathering.deletion_reviewed_by = None
    gathering.save(
        update_fields=[
            "deletion_status",
            "deletion_reason",
            "deletion_requested_at",
            "deletion_reviewed_at",
            "deletion_reviewed_by",
            "updated_at",
        ]
    )
    return gathering


@transaction.atomic
def approve_gathering_deletion(
    *, gathering_id: UUID, community_id: UUID, actor: User
) -> Gathering:
    _assert_can_moderate_deletion(actor=actor)
    gathering = (
        Gathering.all_objects.select_for_update()
        .filter(pk=gathering_id, community_id=community_id)
        .first()
    )
    if gathering is None:
        raise GatheringNotFound("Gathering not found.")
    if gathering.deletion_status != Gathering.DeletionStatus.PENDING:
        raise GatheringDeletionNotPending("No pending deletion request for this gathering.")

    gathering.is_cancelled = True
    gathering.deletion_status = Gathering.DeletionStatus.APPROVED
    gathering.deletion_reviewed_at = timezone.now()
    gathering.deletion_reviewed_by = actor
    gathering.save(
        update_fields=[
            "is_cancelled",
            "deletion_status",
            "deletion_reviewed_at",
            "deletion_reviewed_by",
            "updated_at",
        ]
    )
    record_admin_audit_event(
        actor_id=actor.id,
        action=AdminAuditLog.Action.GATHERING_DELETION_APPROVE,
        metadata={
            "gathering_id": str(gathering.id),
            "title": gathering.title,
            "community_id": str(gathering.community_id),
            "deletion_reason": gathering.deletion_reason,
            "creator_id": str(gathering.creator_id),
        },
    )
    return gathering


@transaction.atomic
def reject_gathering_deletion(
    *, gathering_id: UUID, community_id: UUID, actor: User
) -> Gathering:
    _assert_can_moderate_deletion(actor=actor)
    gathering = (
        Gathering.all_objects.select_for_update()
        .filter(pk=gathering_id, community_id=community_id)
        .first()
    )
    if gathering is None:
        raise GatheringNotFound("Gathering not found.")
    if gathering.deletion_status != Gathering.DeletionStatus.PENDING:
        raise GatheringDeletionNotPending("No pending deletion request for this gathering.")

    gathering.deletion_status = Gathering.DeletionStatus.REJECTED
    gathering.deletion_reviewed_at = timezone.now()
    gathering.deletion_reviewed_by = actor
    gathering.save(
        update_fields=[
            "deletion_status",
            "deletion_reviewed_at",
            "deletion_reviewed_by",
            "updated_at",
        ]
    )
    record_admin_audit_event(
        actor_id=actor.id,
        action=AdminAuditLog.Action.GATHERING_DELETION_REJECT,
        metadata={
            "gathering_id": str(gathering.id),
            "title": gathering.title,
            "community_id": str(gathering.community_id),
            "deletion_reason": gathering.deletion_reason,
            "creator_id": str(gathering.creator_id),
        },
    )
    return gathering


@transaction.atomic
def cancel_gathering(*, gathering_id: UUID, community_id: UUID, actor: User) -> None:
    """Platform admins may cancel immediately; creators must request deletion."""
    gathering = (
        Gathering.all_objects.select_for_update()
        .filter(pk=gathering_id, community_id=community_id)
        .first()
    )
    if gathering is None:
        raise GatheringNotFound("Gathering not found.")
    if not (actor.is_platform_admin or actor.is_superadmin):
        raise GatheringEditForbidden(
            "Creators must request deletion with a reason for admin approval."
        )
    if gathering.is_cancelled:
        return
    gathering.is_cancelled = True
    gathering.deletion_status = Gathering.DeletionStatus.NONE
    gathering.deletion_reviewed_at = timezone.now()
    gathering.deletion_reviewed_by = actor
    gathering.save(
        update_fields=[
            "is_cancelled",
            "deletion_status",
            "deletion_reviewed_at",
            "deletion_reviewed_by",
            "updated_at",
        ]
    )
    record_admin_audit_event(
        actor_id=actor.id,
        action=AdminAuditLog.Action.GATHERING_DELETION_APPROVE,
        metadata={
            "gathering_id": str(gathering.id),
            "title": gathering.title,
            "community_id": str(gathering.community_id),
            "immediate": True,
            "creator_id": str(gathering.creator_id),
        },
    )


@transaction.atomic
def join_gathering(*, gathering_id: UUID, community_id: UUID, user: User) -> GatheringAttendee:
    _assert_identity_verified(user)
    _assert_can_join(user)

    gathering = (
        Gathering.all_objects.select_for_update()
        .filter(pk=gathering_id, community_id=community_id)
        .first()
    )
    if gathering is None:
        raise GatheringNotFound("Gathering not found.")
    if gathering.is_cancelled:
        raise GatheringCancelled("This gathering has been cancelled.")
    if gathering.deletion_status == Gathering.DeletionStatus.APPROVED:
        raise GatheringCancelled("This gathering has been deleted.")
    if gathering.creator_id == user.id:
        raise GatheringCreatorCannotJoin(
            "You created this gathering and cannot join it as an attendee."
        )

    existing = GatheringAttendee.all_objects.filter(gathering=gathering, user=user).first()
    if existing is not None and existing.is_active:
        raise GatheringAlreadyJoined("You already joined this gathering.")

    active_count = GatheringAttendee.all_objects.filter(gathering=gathering, is_active=True).count()
    if active_count >= gathering.max_attendees:
        raise GatheringAtCapacity("This gathering is at capacity.")

    if existing is not None:
        existing.is_active = True
        existing.joined_at = timezone.now()
        existing.save(update_fields=["is_active", "joined_at", "updated_at"])
        return existing

    return GatheringAttendee.all_objects.create(
        gathering=gathering,
        user=user,
        community_id=gathering.community_id,
        city_id=gathering.city_id,
    )


def _extension_for_content_type(content_type: str) -> str:
    normalized = content_type.lower().split(";")[0].strip()
    extension = _CONTENT_TYPE_EXTENSIONS.get(normalized)
    if extension:
        return extension
    guessed = mimetypes.guess_extension(normalized)
    return guessed or ".bin"


def _cover_key_for_uploader(*, uploader_id: UUID, content_type: str) -> str:
    extension = _extension_for_content_type(content_type)
    return f"{settings.GATHERING_COVER_KEY_PREFIX}/{uploader_id}/{uuid.uuid4()}{extension}"


def _validate_cover_object_key(*, uploader_id: UUID, object_key: str) -> None:
    prefix = f"{settings.GATHERING_COVER_KEY_PREFIX}/{uploader_id}/"
    if not object_key.startswith(prefix):
        raise GatheringCoverError("Invalid gathering cover key.")
    if PurePosixPath(object_key).name in {"", ".", ".."}:
        raise GatheringCoverError("Invalid gathering cover key.")


def _assert_cover_object_ready(*, object_key: str, uploader_id: UUID) -> None:
    _validate_cover_object_key(uploader_id=uploader_id, object_key=object_key)
    try:
        metadata = get_object_metadata(object_key)
    except S3StorageError as exc:
        raise GatheringCoverError("Could not verify uploaded file.") from exc
    if metadata is None:
        raise GatheringCoverError("Uploaded file was not found.")
    content_type = metadata["content_type"].lower().split(";")[0].strip()
    if content_type not in settings.GATHERING_COVER_ALLOWED_CONTENT_TYPES:
        raise GatheringCoverError("Unsupported image type.")
    if metadata["content_length"] > settings.GATHERING_COVER_MAX_BYTES:
        raise GatheringCoverError("Image file is too large.")


def create_gathering_cover_upload(
    *,
    uploader: User,
    content_type: str,
    content_length: int,
) -> dict:
    if not is_s3_configured():
        raise GatheringCoverError("File uploads are not configured.")
    normalized_type = content_type.lower().split(";")[0].strip()
    if normalized_type not in settings.GATHERING_COVER_ALLOWED_CONTENT_TYPES:
        raise GatheringCoverError("Unsupported image type.")
    if content_length <= 0 or content_length > settings.GATHERING_COVER_MAX_BYTES:
        raise GatheringCoverError("Image file is too large.")

    object_key = _cover_key_for_uploader(uploader_id=uploader.id, content_type=normalized_type)
    try:
        return generate_presigned_upload_url(
            object_key=object_key,
            content_type=normalized_type,
            content_length=content_length,
            expires_in=settings.GATHERING_COVER_PRESIGNED_EXPIRY,
        )
    except S3StorageError as exc:
        raise GatheringCoverError("Could not create upload URL.") from exc


@transaction.atomic
def confirm_gathering_cover_upload(
    *, gathering_id: UUID, community_id: UUID, object_key: str
) -> Gathering:
    gathering = (
        Gathering.all_objects.select_for_update()
        .filter(pk=gathering_id, community_id=community_id)
        .first()
    )
    if gathering is None:
        raise GatheringNotFound("Gathering not found.")
    _assert_cover_object_ready(object_key=object_key, uploader_id=gathering.creator_id)
    previous_key = gathering.cover_image_key
    gathering.cover_image_key = object_key
    gathering.save(update_fields=["cover_image_key", "updated_at"])
    if previous_key and previous_key != object_key:
        try:
            delete_object(previous_key)
        except S3StorageError:
            logger.exception("Failed to delete previous gathering cover key=%s", previous_key)
    return gathering


@transaction.atomic
def remove_gathering_cover(*, gathering_id: UUID, community_id: UUID) -> Gathering:
    gathering = (
        Gathering.all_objects.select_for_update()
        .filter(pk=gathering_id, community_id=community_id)
        .first()
    )
    if gathering is None:
        raise GatheringNotFound("Gathering not found.")
    previous_key = gathering.cover_image_key
    gathering.cover_image_key = ""
    gathering.save(update_fields=["cover_image_key", "updated_at"])
    if previous_key:
        try:
            delete_object(previous_key)
        except S3StorageError as exc:
            raise GatheringCoverError("Could not delete cover image.") from exc
    return gathering
