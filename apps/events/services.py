from __future__ import annotations

import logging
import mimetypes
import uuid
from decimal import Decimal
from pathlib import PurePosixPath
from typing import Any, Literal
from uuid import UUID

from django.conf import settings
from django.core import signing
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.role_checks import user_has_member_social_access
from apps.events.exceptions import (
    EventAlreadyJoined,
    EventAtCapacity,
    EventCancelled,
    EventCommunityRequired,
    EventCoverError,
    EventEditForbidden,
    EventIdentityRequired,
    EventNotFound,
    JoinRequestNotFound,
    JoinRequestNotPending,
)
from apps.events.models import Event, EventJoinRequest, EventNotification, EventTicket
from apps.notifications.tasks import send_templated_email_task
from apps.tenancy.models import Community
from core.storage import (
    S3StorageError,
    delete_object,
    generate_presigned_upload_url,
    get_object_metadata,
    is_s3_configured,
)

logger = logging.getLogger(__name__)

TICKET_SIGNING_SALT = "events.ticket"


def _iso(value: Any) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def generate_ticket_token(*, user_id: UUID, event_id: UUID) -> str:
    payload = {
        "user_id": str(user_id),
        "event_id": str(event_id),
        "ticket_id": str(uuid.uuid4()),
        "issued_at": timezone.now().isoformat(),
    }
    return signing.dumps(payload, salt=TICKET_SIGNING_SALT)


def verify_ticket_token(token: str, *, max_age: int | None = None) -> dict[str, str]:
    return signing.loads(token, salt=TICKET_SIGNING_SALT, max_age=max_age)


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
    raise EventCommunityRequired("An active community context is required.")


def create_event(
    *,
    creator: User,
    community: Community,
    title: str,
    description: str = "",
    location: str,
    starts_at,
    ends_at,
    price: Decimal = Decimal("0"),
    currency: str | None = None,
    category: str = "",
    capacity: int | None = None,
    cover_image_key: str = "",
) -> Event:
    if cover_image_key:
        _assert_cover_object_ready(object_key=cover_image_key, uploader_id=creator.id)

    return Event.all_objects.create(
        creator=creator,
        community_id=community.id,
        city_id=community.city_id,
        title=title,
        description=description,
        location=location,
        cover_image_key=cover_image_key,
        starts_at=starts_at,
        ends_at=ends_at,
        price=price,
        currency=(currency or settings.DEFAULT_EVENT_CURRENCY).upper(),
        category=category,
        capacity=capacity,
    )


@transaction.atomic
def update_event(*, event_id: UUID, community_id: UUID, **fields: Any) -> Event:
    event = (
        Event.all_objects.select_for_update().filter(pk=event_id, community_id=community_id).first()
    )
    if event is None:
        raise EventNotFound("Event not found.")

    if "price" in fields and fields["price"] != event.price:
        raise EventEditForbidden("Price cannot be changed after creation.")
    if "location" in fields and fields["location"] != event.location:
        raise EventEditForbidden("Location cannot be changed after creation.")

    if "cover_image_key" in fields and fields["cover_image_key"]:
        _assert_cover_object_ready(
            object_key=fields["cover_image_key"],
            uploader_id=event.creator_id,
        )

    if "currency" in fields and fields["currency"]:
        fields["currency"] = str(fields["currency"]).upper()

    was_cancelled = event.is_cancelled
    notify_update = False
    previous_cover = event.cover_image_key
    for key, value in fields.items():
        if hasattr(event, key) and getattr(event, key) != value:
            setattr(event, key, value)
            if key in {
                "title",
                "description",
                "starts_at",
                "ends_at",
                "capacity",
                "cover_image_key",
            }:
                notify_update = True

    event.save()

    if "cover_image_key" in fields and previous_cover and previous_cover != event.cover_image_key:
        try:
            delete_object(previous_cover)
        except S3StorageError:
            logger.exception("Failed to delete previous event cover key=%s", previous_cover)

    if not was_cancelled and event.is_cancelled:
        from apps.events.tasks import deliver_event_change_notifications_task

        deliver_event_change_notifications_task.delay(str(event.id), "cancelled")
    elif notify_update and not event.is_cancelled:
        from apps.events.tasks import deliver_event_change_notifications_task

        deliver_event_change_notifications_task.delay(str(event.id), "updated")

    return event


@transaction.atomic
def delete_event(*, event_id: UUID, community_id: UUID) -> None:
    """Soft-delete via cancel so ticket holders still receive cancellation notices."""
    event = (
        Event.all_objects.select_for_update().filter(pk=event_id, community_id=community_id).first()
    )
    if event is None:
        raise EventNotFound("Event not found.")
    if event.is_cancelled:
        return

    event.is_cancelled = True
    event.save(update_fields=["is_cancelled", "updated_at"])

    from apps.events.tasks import deliver_event_change_notifications_task

    deliver_event_change_notifications_task.delay(str(event.id), "cancelled")


def _assert_event_joinable(event: Event) -> None:
    if event.is_cancelled:
        raise EventCancelled("This event has been cancelled.")


def _assert_capacity(event: Event) -> None:
    if event.capacity is None:
        return
    active = EventTicket.all_objects.filter(event=event, is_active=True).count()
    if active >= event.capacity:
        raise EventAtCapacity("This event is at capacity.")


@transaction.atomic
def create_event_ticket(*, event: Event, user: User) -> EventTicket:
    """Issue a signed ticket. Payment gating lands with Milestone 4."""
    locked = Event.all_objects.select_for_update().get(pk=event.pk)
    _assert_event_joinable(locked)

    if EventTicket.all_objects.filter(event=locked, user=user).exists():
        raise EventAlreadyJoined("User already has a ticket for this event.")

    _assert_capacity(locked)

    token = generate_ticket_token(user_id=user.id, event_id=locked.id)
    return EventTicket.all_objects.create(
        event=locked,
        user=user,
        community_id=locked.community_id,
        city_id=locked.city_id,
        token=token,
    )


class TicketScanError(Exception):
    """Raised when a ticket cannot be marked as scanned."""


@transaction.atomic
def mark_ticket_scanned(*, ticket_id: UUID, scanned_at=None) -> EventTicket:
    """Record venue check-in. Attendance for gatherings requires this scan."""
    from django.utils import timezone

    ticket = (
        EventTicket.all_objects.select_for_update()
        .select_related("event")
        .filter(pk=ticket_id, is_active=True)
        .first()
    )
    if ticket is None:
        raise TicketScanError("Ticket not found.")
    if ticket.event.is_cancelled:
        raise TicketScanError("Event is cancelled.")
    if ticket.scanned_at is not None:
        return ticket
    ticket.scanned_at = scanned_at or timezone.now()
    ticket.save(update_fields=["scanned_at", "updated_at"])
    return ticket


def create_event_notification(
    *,
    event: Event,
    user: User,
    notification_type: str,
    title: str,
    message: str,
) -> EventNotification:
    return EventNotification.all_objects.create(
        event=event,
        user=user,
        community_id=event.community_id,
        city_id=event.city_id,
        notification_type=notification_type,
        title=title,
        message=message,
    )


@transaction.atomic
def join_event(*, event_id: UUID, user: User) -> tuple[str, EventTicket | EventJoinRequest]:
    if not (user.is_platform_admin or user.is_superadmin or user.is_identity_verified):
        raise EventIdentityRequired("Verify your identity before joining an event.")

    event = Event.all_objects.select_for_update().filter(pk=event_id).first()
    if event is None:
        raise EventNotFound("Event not found.")
    _assert_event_joinable(event)

    if EventTicket.all_objects.filter(event=event, user=user).exists():
        raise EventAlreadyJoined("You already have a ticket for this event.")

    # Members + City Founders join instantly (FR 41). Payment gates later in M4.
    if user_has_member_social_access(user):
        ticket = create_event_ticket(event=event, user=user)
        from apps.events.tasks import deliver_event_ticket_notification_task

        ticket_id = str(ticket.id)
        # Enqueue after commit so a broker blip never rolls back the ticket.
        transaction.on_commit(
            lambda: deliver_event_ticket_notification_task.delay(ticket_id)
        )
        return "ticket", ticket

    # Non-Members must request; City Founder approves (FR 42, 167).
    existing = (
        EventJoinRequest.all_objects.select_for_update()
        .filter(event=event, user=user)
        .order_by("-requested_at")
        .first()
    )
    if existing is not None:
        if existing.status == EventJoinRequest.Status.PENDING:
            return "join_request", existing
        if existing.status == EventJoinRequest.Status.APPROVED:
            return "join_request", existing
        if existing.status == EventJoinRequest.Status.REJECTED:
            existing.status = EventJoinRequest.Status.PENDING
            existing.responded_at = None
            existing.notes = ""
            existing.save(
                update_fields=["status", "responded_at", "notes", "updated_at"]
            )
            return "join_request", existing

    join_request = EventJoinRequest.all_objects.create(
        event=event,
        user=user,
        community_id=event.community_id,
        city_id=event.city_id,
        status=EventJoinRequest.Status.PENDING,
    )
    return "join_request", join_request


@transaction.atomic
def respond_to_join_request(
    *,
    event_id: UUID,
    request_id: UUID,
    community_id: UUID,
    approve: bool,
) -> EventJoinRequest:
    join_request = (
        EventJoinRequest.all_objects.select_for_update()
        .select_related("event", "user")
        .filter(pk=request_id, event_id=event_id, community_id=community_id)
        .first()
    )
    if join_request is None:
        raise JoinRequestNotFound("Join request not found.")
    if join_request.status != EventJoinRequest.Status.PENDING:
        raise JoinRequestNotPending("Join request is not pending.")

    join_request.status = (
        EventJoinRequest.Status.APPROVED if approve else EventJoinRequest.Status.REJECTED
    )
    join_request.responded_at = timezone.now()
    join_request.save(update_fields=["status", "responded_at", "updated_at"])

    if approve:
        # Until Milestone 4 payment gating: founder approval fully admits the
        # attendee (same as Member instant join) — issue ticket + notify.
        from apps.events.tasks import deliver_event_ticket_notification_task

        try:
            ticket = create_event_ticket(
                event=join_request.event, user=join_request.user
            )
        except EventAlreadyJoined:
            ticket = (
                EventTicket.all_objects.filter(
                    event=join_request.event, user=join_request.user
                )
                .order_by("-issued_at")
                .first()
            )
        if ticket is not None:
            ticket_id = str(ticket.id)
            transaction.on_commit(
                lambda: deliver_event_ticket_notification_task.delay(ticket_id)
            )

    return join_request


@transaction.atomic
def fulfill_approved_joins_for_user(*, user_id: UUID) -> int:
    """Backfill tickets for founder-approved requests that never received one."""
    approved = (
        EventJoinRequest.all_objects.filter(
            user_id=user_id,
            status=EventJoinRequest.Status.APPROVED,
        )
        .select_related("event", "user")
        .order_by("-requested_at")
    )
    created = 0
    for join_request in approved:
        if EventTicket.all_objects.filter(
            event_id=join_request.event_id, user_id=user_id, is_active=True
        ).exists():
            continue
        try:
            create_event_ticket(event=join_request.event, user=join_request.user)
            created += 1
        except (EventAlreadyJoined, EventAtCapacity, EventCancelled):
            continue
    return created


@transaction.atomic
def fulfill_approved_join_for_event(*, event: Event, user: User) -> EventTicket | None:
    """Issue a missing ticket when opening an event after founder approval."""
    if EventTicket.all_objects.filter(event=event, user=user, is_active=True).exists():
        return None
    join_request = (
        EventJoinRequest.all_objects.filter(
            event=event,
            user=user,
            status=EventJoinRequest.Status.APPROVED,
        )
        .order_by("-requested_at")
        .first()
    )
    if join_request is None:
        return None
    try:
        return create_event_ticket(event=event, user=user)
    except (EventAlreadyJoined, EventAtCapacity, EventCancelled):
        return (
            EventTicket.all_objects.filter(event=event, user=user, is_active=True)
            .order_by("-issued_at")
            .first()
        )


@transaction.atomic
def issue_ticket_after_payment(*, event_id: UUID, user_id: UUID) -> EventTicket:
    """Called by payments webhook once Milestone 4 lands."""
    event = Event.all_objects.select_for_update().filter(pk=event_id).first()
    if event is None:
        raise EventNotFound("Event not found.")
    user = User.objects.get(pk=user_id)
    ticket = create_event_ticket(event=event, user=user)
    from apps.events.tasks import deliver_event_ticket_notification_task

    ticket_id = str(ticket.id)
    transaction.on_commit(
        lambda: deliver_event_ticket_notification_task.delay(ticket_id)
    )
    return ticket


def _send_whatsapp_message(phone_number: str | None, message: str) -> None:
    # WhatsApp Business API lands with Milestone 3 notifications work.
    if not phone_number:
        logger.debug("No phone number available for WhatsApp delivery.")
        return
    logger.info("WhatsApp message queued for %s: %s", phone_number, message)


def _ticket_email_context(event: Event, ticket: EventTicket) -> dict[str, str]:
    return {
        "recipient_name": ticket.user.full_name or ticket.user.email,
        "event_title": event.title,
        "event_location": event.location,
        "event_start": _iso(event.starts_at),
        "event_end": _iso(event.ends_at),
        "ticket_token": ticket.token,
        "ticket_qr_payload": ticket.token,
        "preheader": "Your Mixed Miles ticket is ready.",
    }


def _change_email_context(
    event: Event, user: User, change_type: Literal["updated", "cancelled"]
) -> dict[str, str]:
    message = (
        "This event has been cancelled."
        if change_type == "cancelled"
        else "Details have changed for this event."
    )
    return {
        "recipient_name": user.full_name or user.email,
        "event_title": event.title,
        "event_location": event.location,
        "event_start": _iso(event.starts_at),
        "event_end": _iso(event.ends_at),
        "change_message": message,
        "preheader": message,
    }


@transaction.atomic
def deliver_event_ticket_notification(ticket_id: UUID) -> str:
    ticket = EventTicket.all_objects.select_related("event", "user").filter(pk=ticket_id).first()
    if ticket is None:
        raise EventNotFound("Ticket not found.")

    event = ticket.event
    user = ticket.user
    subject = f"Your ticket for {event.title}"
    context = _ticket_email_context(event, ticket)

    if user.email:
        send_templated_email_task.delay(
            to=user.email,
            subject=subject,
            template_basename="event_ticket",
            context=context,
        )

    create_event_notification(
        event=event,
        user=user,
        notification_type=EventNotification.NotificationType.TICKET,
        title=subject,
        message=f"Your ticket for {event.title} is ready.",
    )
    _send_whatsapp_message(user.phone_number, f"Your ticket for {event.title} is ready.")
    return ticket.token


@transaction.atomic
def deliver_event_invitation_notification(join_request_id: UUID) -> None:
    join_request = (
        EventJoinRequest.all_objects.select_related("event", "user")
        .filter(pk=join_request_id)
        .first()
    )
    if join_request is None:
        raise JoinRequestNotFound("Join request not found.")

    event = join_request.event
    user = join_request.user
    subject = f"You're approved for {event.title}"
    context = {
        "recipient_name": user.full_name or user.email,
        "event_title": event.title,
        "event_location": event.location,
        "event_start": _iso(event.starts_at),
        "event_end": _iso(event.ends_at),
        "preheader": "Complete payment to receive your ticket.",
    }

    if user.email:
        send_templated_email_task.delay(
            to=user.email,
            subject=subject,
            template_basename="event_invitation",
            context=context,
        )

    create_event_notification(
        event=event,
        user=user,
        notification_type=EventNotification.NotificationType.INVITATION,
        title=subject,
        message=(
            f"Your join request for {event.title} was approved. "
            "Complete payment to get your ticket."
        ),
    )
    _send_whatsapp_message(
        user.phone_number,
        f"Approved for {event.title}. Complete payment in the app to receive your ticket.",
    )


@transaction.atomic
def deliver_event_change_notifications(
    event_id: UUID, change_type: Literal["updated", "cancelled"]
) -> int:
    event = Event.all_objects.filter(pk=event_id).first()
    if event is None:
        raise EventNotFound("Event not found.")

    tickets = EventTicket.all_objects.filter(event=event, is_active=True).select_related("user")
    sent_count = 0
    for ticket in tickets:
        user = ticket.user
        subject = (
            f"Event cancelled: {event.title}"
            if change_type == "cancelled"
            else f"Event updated: {event.title}"
        )
        context = _change_email_context(event, user, change_type)

        if user.email:
            send_templated_email_task.delay(
                to=user.email,
                subject=subject,
                template_basename="event_change",
                context=context,
            )

        create_event_notification(
            event=event,
            user=user,
            notification_type=(
                EventNotification.NotificationType.CANCELLATION
                if change_type == "cancelled"
                else EventNotification.NotificationType.UPDATE
            ),
            title=subject,
            message=context["change_message"],
        )
        _send_whatsapp_message(user.phone_number, context["change_message"])
        sent_count += 1

    return sent_count


def active_attendee_count(event: Event) -> int:
    return EventTicket.all_objects.filter(event=event, is_active=True).count()


def event_nationality_breakdown(event: Event) -> dict[str, int]:
    rows = (
        EventTicket.all_objects.filter(event=event, is_active=True)
        .values("user__nationality_code")
        .annotate(count=Count("id"))
    )
    return {(row["user__nationality_code"] or "unknown"): row["count"] for row in rows}


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


def _cover_key_for_uploader(*, uploader_id: UUID, content_type: str) -> str:
    extension = _extension_for_content_type(content_type)
    return f"{settings.EVENT_COVER_KEY_PREFIX}/{uploader_id}/{uuid.uuid4()}{extension}"


def _validate_cover_object_key(*, uploader_id: UUID, object_key: str) -> None:
    prefix = f"{settings.EVENT_COVER_KEY_PREFIX}/{uploader_id}/"
    if not object_key.startswith(prefix):
        raise EventCoverError("Invalid event cover key.")
    if PurePosixPath(object_key).name in {"", ".", ".."}:
        raise EventCoverError("Invalid event cover key.")


def _assert_cover_object_ready(*, object_key: str, uploader_id: UUID) -> None:
    _validate_cover_object_key(uploader_id=uploader_id, object_key=object_key)
    try:
        metadata = get_object_metadata(object_key)
    except S3StorageError as exc:
        raise EventCoverError("Could not verify uploaded file.") from exc
    if metadata is None:
        raise EventCoverError("Uploaded file was not found.")

    content_type = metadata["content_type"].lower().split(";")[0].strip()
    if content_type not in settings.EVENT_COVER_ALLOWED_CONTENT_TYPES:
        raise EventCoverError("Unsupported image type.")
    if metadata["content_length"] > settings.EVENT_COVER_MAX_BYTES:
        raise EventCoverError("Image file is too large.")


def create_event_cover_upload(
    *,
    uploader: User,
    content_type: str,
    content_length: int,
) -> dict:
    if not is_s3_configured():
        raise EventCoverError("File uploads are not configured.")

    normalized_type = content_type.lower().split(";")[0].strip()
    if normalized_type not in settings.EVENT_COVER_ALLOWED_CONTENT_TYPES:
        raise EventCoverError("Unsupported image type.")
    if content_length <= 0 or content_length > settings.EVENT_COVER_MAX_BYTES:
        raise EventCoverError("Image file is too large.")

    object_key = _cover_key_for_uploader(uploader_id=uploader.id, content_type=normalized_type)
    try:
        return generate_presigned_upload_url(
            object_key=object_key,
            content_type=normalized_type,
            content_length=content_length,
            expires_in=settings.EVENT_COVER_PRESIGNED_EXPIRY,
        )
    except S3StorageError as exc:
        raise EventCoverError("Could not create upload URL.") from exc


@transaction.atomic
def confirm_event_cover_upload(*, event_id: UUID, community_id: UUID, object_key: str) -> Event:
    event = (
        Event.all_objects.select_for_update().filter(pk=event_id, community_id=community_id).first()
    )
    if event is None:
        raise EventNotFound("Event not found.")

    _assert_cover_object_ready(object_key=object_key, uploader_id=event.creator_id)
    previous_key = event.cover_image_key
    event.cover_image_key = object_key
    event.save(update_fields=["cover_image_key", "updated_at"])

    if previous_key and previous_key != object_key:
        try:
            delete_object(previous_key)
        except S3StorageError:
            logger.exception("Failed to delete previous event cover key=%s", previous_key)

    return event


@transaction.atomic
def remove_event_cover(*, event_id: UUID, community_id: UUID) -> Event:
    event = (
        Event.all_objects.select_for_update().filter(pk=event_id, community_id=community_id).first()
    )
    if event is None:
        raise EventNotFound("Event not found.")

    previous_key = event.cover_image_key
    event.cover_image_key = ""
    event.save(update_fields=["cover_image_key", "updated_at"])

    if previous_key:
        try:
            delete_object(previous_key)
        except S3StorageError as exc:
            raise EventCoverError("Could not delete cover image.") from exc

    return event
