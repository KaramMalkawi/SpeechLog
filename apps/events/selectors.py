from __future__ import annotations

from collections import defaultdict
from datetime import date
from uuid import UUID

from django.conf import settings
from django.db.models import Count, Q, QuerySet

from apps.accounts.models import User
from apps.accounts.profile_selectors import get_profile_photo_url
from apps.accounts.role_checks import user_has_member_social_access
from apps.events.models import Event, EventJoinRequest, EventTicket
from apps.tenancy.selectors import get_city_by_id
from core.storage import build_media_url


def _annotate_attendee_count(qs: QuerySet[Event]) -> QuerySet[Event]:
    return qs.annotate(
        attendee_count=Count("tickets", filter=Q(tickets__is_active=True), distinct=True)
    )


def list_events(
    *,
    community_id: UUID,
    city_id: UUID | None = None,
    category: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    include_cancelled: bool = False,
) -> QuerySet[Event]:
    """Community-isolated event list. City/date/category are filters within that tenant."""
    qs = Event.all_objects.filter(community_id=community_id)
    if not include_cancelled:
        qs = qs.filter(is_cancelled=False)
    if city_id is not None:
        qs = qs.filter(city_id=city_id)
    if category:
        qs = qs.filter(category=category)
    if start_date is not None:
        qs = qs.filter(starts_at__date__gte=start_date)
    if end_date is not None:
        qs = qs.filter(starts_at__date__lte=end_date)
    return _annotate_attendee_count(qs).select_related("creator").order_by("starts_at", "title")


def get_event_for_community(*, event_id: UUID, community_id: UUID) -> Event | None:
    return (
        _annotate_attendee_count(Event.all_objects.filter(pk=event_id, community_id=community_id))
        .select_related("creator")
        .first()
    )


def get_event_by_id(*, event_id: UUID) -> Event | None:
    return (
        _annotate_attendee_count(Event.all_objects.filter(pk=event_id))
        .select_related("creator")
        .first()
    )


def list_pending_join_requests(*, event_id: UUID, community_id: UUID) -> QuerySet[EventJoinRequest]:
    return (
        EventJoinRequest.all_objects.filter(
            event_id=event_id,
            community_id=community_id,
            status=EventJoinRequest.Status.PENDING,
        )
        .select_related("user", "event")
        .order_by("requested_at")
    )


def list_event_attendees(*, event_id: UUID, community_id: UUID) -> QuerySet[EventTicket]:
    return (
        EventTicket.all_objects.filter(
            event_id=event_id,
            community_id=community_id,
            is_active=True,
        )
        .select_related("user", "event")
        .order_by("issued_at")
    )


def list_my_tickets(*, user_id: UUID) -> QuerySet[EventTicket]:
    # Ordering must match IssuedAtCursorPagination (issued_at, id).
    return (
        EventTicket.all_objects.filter(user_id=user_id, is_active=True)
        .select_related("event")
        .order_by("issued_at", "id")
    )


def count_attended_events(*, user_id: UUID) -> int:
    """Distinct events the user has checked into (ticket scanned on event day)."""
    return (
        EventTicket.all_objects.filter(
            user_id=user_id,
            is_active=True,
            scanned_at__isnull=False,
        )
        .values("event_id")
        .distinct()
        .count()
    )


def nationality_breakdown_for_event(*, event_id: UUID, community_id: UUID) -> dict[str, int]:
    rows = (
        EventTicket.all_objects.filter(
            event_id=event_id,
            community_id=community_id,
            is_active=True,
        )
        .values("user__nationality_code")
        .annotate(count=Count("id"))
    )
    breakdown: dict[str, int] = {}
    for row in rows:
        key = row["user__nationality_code"] or "unknown"
        breakdown[key] = row["count"]
    return breakdown


def get_cover_image_url(event: Event) -> str:
    return build_media_url(event.cover_image_key)


def build_attendee_preview(*, user: User) -> dict:
    return {
        "user_id": user.id,
        "full_name": user.full_name,
        "photo_url": get_profile_photo_url(user),
    }


def attendee_previews_for_events(
    *,
    event_ids: list[UUID],
    limit: int | None = None,
) -> dict[UUID, list[dict]]:
    if not event_ids:
        return {}
    preview_limit = limit or settings.EVENT_ATTENDEE_PREVIEW_LIMIT
    tickets = (
        EventTicket.all_objects.filter(event_id__in=event_ids, is_active=True)
        .select_related("user")
        .order_by("event_id", "issued_at")
    )
    grouped: dict[UUID, list[dict]] = defaultdict(list)
    for ticket in tickets:
        bucket = grouped[ticket.event_id]
        if len(bucket) >= preview_limit:
            continue
        bucket.append(build_attendee_preview(user=ticket.user))
    return dict(grouped)


def build_organizer_payload(*, creator: User, city_id: UUID) -> dict:
    city = get_city_by_id(city_id)
    city_name = city.name if city is not None else ""
    if creator.role == User.Role.CITY_FOUNDER:
        role_label = f"City Founder · {city_name}" if city_name else "City Founder"
    else:
        role_label = creator.get_role_display()
    return {
        "id": creator.id,
        "full_name": creator.full_name,
        "photo_url": get_profile_photo_url(creator),
        "role": creator.role,
        "role_label": role_label,
    }


def get_viewer_join_status(*, event: Event, viewer: User | None) -> str:
    if viewer is None or not viewer.is_authenticated:
        return "none"
    if EventTicket.all_objects.filter(event=event, user=viewer, is_active=True).exists():
        return "joined"
    join_request = (
        EventJoinRequest.all_objects.filter(event=event, user=viewer)
        .order_by("-requested_at")
        .first()
    )
    if join_request is None:
        return "none"
    if join_request.status == EventJoinRequest.Status.PENDING:
        return "pending"
    if join_request.status == EventJoinRequest.Status.APPROVED:
        return "approved"
    return "none"


def viewer_requires_approval(*, viewer: User | None) -> bool:
    """Non-Members need City Founder approval; Members/City Founders join instantly (FR 41–42)."""
    if viewer is None or not viewer.is_authenticated:
        return True
    return not user_has_member_social_access(viewer)


def spots_left_for_event(*, event: Event, attendee_count: int) -> int | None:
    if event.capacity is None:
        return None
    return max(event.capacity - attendee_count, 0)
