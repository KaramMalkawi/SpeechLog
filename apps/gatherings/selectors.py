from __future__ import annotations

from collections import defaultdict
from datetime import date
from uuid import UUID

from django.conf import settings
from django.db.models import Count, F, Q, QuerySet

from apps.accounts.models import User
from apps.accounts.profile_selectors import get_profile_photo_url
from apps.events.selectors import count_attended_events
from apps.gatherings.models import Gathering, GatheringAttendee
from apps.tenancy.selectors import get_city_by_id
from core.storage import build_media_url


def _annotate_attendee_count(qs: QuerySet[Gathering]) -> QuerySet[Gathering]:
    return qs.annotate(
        attendee_count=Count(
            "attendees",
            filter=Q(attendees__is_active=True) & ~Q(attendees__user_id=F("creator_id")),
            distinct=True,
        )
    )


def list_gatherings(
    *,
    community_id: UUID,
    city_id: UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    include_cancelled: bool = False,
) -> QuerySet[Gathering]:
    qs = Gathering.all_objects.filter(community_id=community_id)
    if not include_cancelled:
        qs = qs.filter(is_cancelled=False)
    qs = qs.exclude(deletion_status=Gathering.DeletionStatus.APPROVED)
    if city_id is not None:
        qs = qs.filter(city_id=city_id)
    if start_date is not None:
        qs = qs.filter(starts_at__date__gte=start_date)
    if end_date is not None:
        qs = qs.filter(starts_at__date__lte=end_date)
    return _annotate_attendee_count(qs).select_related("creator").order_by("-created_at", "title")


def get_gathering_for_community(*, gathering_id: UUID, community_id: UUID) -> Gathering | None:
    return (
        _annotate_attendee_count(
            Gathering.all_objects.filter(
                pk=gathering_id,
                community_id=community_id,
                is_cancelled=False,
            )
        )
        .select_related("creator")
        .first()
    )


def get_gathering_by_id(*, gathering_id: UUID) -> Gathering | None:
    return (
        _annotate_attendee_count(
            Gathering.all_objects.filter(
                pk=gathering_id,
                is_cancelled=False,
            ).exclude(deletion_status=Gathering.DeletionStatus.APPROVED)
        )
        .select_related("creator")
        .first()
    )


def list_gathering_attendees(
    *, gathering_id: UUID, community_id: UUID
) -> QuerySet[GatheringAttendee]:
    return (
        GatheringAttendee.all_objects.filter(
            gathering_id=gathering_id,
            community_id=community_id,
            is_active=True,
        )
        .select_related("user", "gathering")
        .order_by("joined_at")
    )


def list_my_gatherings(*, user_id: UUID) -> QuerySet[GatheringAttendee]:
    return (
        GatheringAttendee.all_objects.filter(user_id=user_id, is_active=True)
        .select_related("gathering", "gathering__creator")
        .order_by("-gathering__created_at")
    )


def list_my_joined_gatherings(*, user_id: UUID) -> QuerySet[Gathering]:
    return (
        _annotate_attendee_count(
            Gathering.all_objects.filter(
                attendees__user_id=user_id,
                attendees__is_active=True,
                is_cancelled=False,
            ).exclude(creator_id=user_id)
            .exclude(deletion_status=Gathering.DeletionStatus.APPROVED)
        )
        .select_related("creator")
        .distinct()
        .order_by("-created_at", "title")
    )


def list_my_created_gatherings(*, user_id: UUID) -> QuerySet[Gathering]:
    return (
        _annotate_attendee_count(
            Gathering.all_objects.filter(
                creator_id=user_id,
                is_cancelled=False,
            ).exclude(deletion_status=Gathering.DeletionStatus.APPROVED)
        )
        .select_related("creator")
        .order_by("-created_at", "title")
    )


def list_pending_deletion_gatherings() -> QuerySet[Gathering]:
    return (
        _annotate_attendee_count(
            Gathering.all_objects.filter(
                deletion_status=Gathering.DeletionStatus.PENDING,
                is_cancelled=False,
            )
        )
        .select_related("creator", "deletion_reviewed_by")
        .order_by("-deletion_requested_at", "-created_at")
    )


def get_cover_image_url(gathering: Gathering) -> str:
    return build_media_url(gathering.cover_image_key)


def build_attendee_preview(*, user: User) -> dict:
    return {
        "user_id": user.id,
        "full_name": user.full_name,
        "photo_url": get_profile_photo_url(user),
    }


def attendee_previews_for_gatherings(
    *,
    gathering_ids: list[UUID],
    limit: int | None = None,
) -> dict[UUID, list[dict]]:
    if not gathering_ids:
        return {}
    preview_limit = limit or settings.EVENT_ATTENDEE_PREVIEW_LIMIT
    rows = (
        GatheringAttendee.all_objects.filter(
            gathering_id__in=gathering_ids,
            is_active=True,
        )
        .select_related("user")
        .order_by("gathering_id", "joined_at")
    )
    grouped: dict[UUID, list[dict]] = defaultdict(list)
    for row in rows:
        bucket = grouped[row.gathering_id]
        if len(bucket) >= preview_limit:
            continue
        bucket.append(build_attendee_preview(user=row.user))
    return dict(grouped)


def build_organizer_payload(*, creator: User, city_id: UUID) -> dict:
    city = get_city_by_id(city_id)
    city_name = city.name if city is not None else ""
    if creator.role == User.Role.CITY_FOUNDER:
        role_label = f"City Founder · {city_name}" if city_name else "City Founder"
    elif creator.role == User.Role.MEMBER:
        role_label = "Member"
    else:
        role_label = creator.get_role_display()
    return {
        "id": creator.id,
        "full_name": creator.full_name,
        "photo_url": get_profile_photo_url(creator),
        "role": creator.role,
        "role_label": role_label,
    }


def viewer_is_creator(*, gathering: Gathering, viewer: User | None) -> bool:
    if viewer is None or not viewer.is_authenticated:
        return False
    return gathering.creator_id == viewer.id


def viewer_has_joined(*, gathering: Gathering, viewer: User | None) -> bool:
    if viewer is None or not viewer.is_authenticated:
        return False
    if viewer_is_creator(gathering=gathering, viewer=viewer):
        return False
    return GatheringAttendee.all_objects.filter(
        gathering=gathering,
        user=viewer,
        is_active=True,
    ).exists()


def viewer_can_see_location(*, gathering: Gathering, viewer: User | None) -> bool:
    if viewer_is_creator(gathering=gathering, viewer=viewer):
        return True
    if viewer is not None and (
        getattr(viewer, "is_platform_admin", False) or getattr(viewer, "is_superadmin", False)
    ):
        return True
    return viewer_has_joined(gathering=gathering, viewer=viewer)


def get_viewer_join_status(*, gathering: Gathering, viewer: User | None) -> str:
    if viewer_is_creator(gathering=gathering, viewer=viewer):
        return "creator"
    if viewer_has_joined(gathering=gathering, viewer=viewer):
        return "joined"
    return "none"


def spots_left_for_gathering(*, gathering: Gathering, attendee_count: int) -> int:
    return max(gathering.max_attendees - attendee_count, 0)


def required_events_attended(*, user: User) -> int:
    """
    Gathering create/join gate (FR):
    - Member / City Founder → 1 attended (scanned) event
    - Non-Member → 3 attended events
    """
    if user.role in {User.Role.MEMBER, User.Role.CITY_FOUNDER}:
        return 1
    if user.role == User.Role.NON_MEMBER:
        return 3
    return 0


def get_create_eligibility(*, user: User) -> dict:
    scanned = count_attended_events(user_id=user.id)
    credit = int(getattr(user, "gathering_attendance_credit", 0) or 0)
    attended = scanned + credit
    required = required_events_attended(user=user)
    bypass = bool(getattr(user, "bypass_gathering_attendance", False))
    # FR: Non-Member unlocks at 3 or more (>= 3); Member/Founder at 1 or more.
    eligible = bypass or attended >= required
    if user.role == User.Role.MEMBER:
        role_label = "Member"
    elif user.role == User.Role.CITY_FOUNDER:
        role_label = "City Founder"
    elif user.role == User.Role.NON_MEMBER:
        role_label = "Non-Member"
    else:
        role_label = user.get_role_display() if hasattr(user, "get_role_display") else str(user.role)
    return {
        "can_create": eligible,
        "can_join": eligible,
        "events_attended": attended,
        "events_scanned": scanned,
        "attendance_credit": credit,
        "events_required": required,
        "bypass_gathering_attendance": bypass,
        "role": user.role,
        "role_label": role_label,
    }


def get_join_eligibility(*, user: User) -> dict:
    # Same thresholds as create (FR 37–38).
    return get_create_eligibility(user=user)
