from __future__ import annotations

from typing import Any

from rest_framework import serializers

from apps.accounts.models import User
from apps.accounts.profile_selectors import get_profile_photo_url
from apps.gatherings.models import GATHERING_HARD_CAP, Gathering, GatheringAttendee
from apps.gatherings.selectors import (
    build_organizer_payload,
    get_cover_image_url,
    get_viewer_join_status,
    spots_left_for_gathering,
    viewer_can_see_location,
    viewer_has_joined,
    viewer_is_creator,
)


class GatheringOrganizerSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    full_name = serializers.CharField()
    photo_url = serializers.CharField(allow_blank=True)
    role = serializers.CharField()
    role_label = serializers.CharField()


class GatheringAttendeePreviewSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    full_name = serializers.CharField()
    photo_url = serializers.CharField(allow_blank=True)


class GatheringSerializer(serializers.ModelSerializer):
    cover_image_url = serializers.SerializerMethodField()
    attendee_count = serializers.IntegerField(read_only=True)
    attendee_previews = serializers.SerializerMethodField()
    attendee_extra_count = serializers.SerializerMethodField()
    spots_total = serializers.IntegerField(source="max_attendees", read_only=True)
    spots_left = serializers.SerializerMethodField()
    hard_cap = serializers.SerializerMethodField()
    organizer = serializers.SerializerMethodField()
    viewer_join_status = serializers.SerializerMethodField()
    viewer_is_creator = serializers.SerializerMethodField()
    viewer_can_edit = serializers.SerializerMethodField()
    viewer_can_join = serializers.SerializerMethodField()
    viewer_unlock_hint = serializers.SerializerMethodField()
    deletion_status = serializers.CharField(read_only=True)
    deletion_reason = serializers.SerializerMethodField()
    deletion_requested_at = serializers.DateTimeField(read_only=True)
    # Exact pin only when the viewer has joined or is the creator (FR 34).
    exact_location = serializers.SerializerMethodField()
    map_link = serializers.SerializerMethodField()
    location_revealed = serializers.SerializerMethodField()

    class Meta:
        model = Gathering
        fields = [
            "id",
            "title",
            "description",
            "area",
            "exact_location",
            "map_link",
            "location_revealed",
            "cover_image_url",
            "starts_at",
            "ends_at",
            "max_attendees",
            "hard_cap",
            "spots_total",
            "spots_left",
            "is_cancelled",
            "deletion_status",
            "deletion_reason",
            "deletion_requested_at",
            "creator_id",
            "organizer",
            "community_id",
            "city_id",
            "attendee_count",
            "attendee_previews",
            "attendee_extra_count",
            "viewer_join_status",
            "viewer_is_creator",
            "viewer_can_edit",
            "viewer_can_join",
            "viewer_unlock_hint",
        ]
        read_only_fields = fields

    def _viewer(self) -> User | None:
        request = self.context.get("request")
        if request is None:
            return None
        user = getattr(request, "user", None)
        if user is not None and getattr(user, "is_authenticated", False):
            return user
        return None

    def _attendee_count(self, gathering: Gathering) -> int:
        return int(getattr(gathering, "attendee_count", 0) or 0)

    def _joined(self, gathering: Gathering) -> bool:
        return viewer_has_joined(gathering=gathering, viewer=self._viewer())

    def _is_creator(self, gathering: Gathering) -> bool:
        return viewer_is_creator(gathering=gathering, viewer=self._viewer())

    def get_cover_image_url(self, gathering: Gathering) -> str:
        return get_cover_image_url(gathering)

    def get_attendee_previews(self, gathering: Gathering) -> list[dict]:
        previews_map = self.context.get("attendee_previews") or {}
        return previews_map.get(gathering.id, [])

    def get_attendee_extra_count(self, gathering: Gathering) -> int:
        previews = self.get_attendee_previews(gathering)
        return max(self._attendee_count(gathering) - len(previews), 0)

    def get_spots_left(self, gathering: Gathering) -> int:
        return spots_left_for_gathering(
            gathering=gathering, attendee_count=self._attendee_count(gathering)
        )

    def get_hard_cap(self, gathering: Gathering) -> int:
        return GATHERING_HARD_CAP

    def get_organizer(self, gathering: Gathering) -> dict:
        return build_organizer_payload(creator=gathering.creator, city_id=gathering.city_id)

    def get_viewer_join_status(self, gathering: Gathering) -> str:
        return get_viewer_join_status(gathering=gathering, viewer=self._viewer())

    def get_viewer_is_creator(self, gathering: Gathering) -> bool:
        return self._is_creator(gathering)

    def get_viewer_can_edit(self, gathering: Gathering) -> bool:
        viewer = self._viewer()
        if viewer is None:
            return False
        if gathering.is_cancelled:
            return False
        if gathering.deletion_status == Gathering.DeletionStatus.PENDING:
            # Edits are blocked while the deletion request is pending.
            return bool(
                getattr(viewer, "is_platform_admin", False)
                or getattr(viewer, "is_superadmin", False)
            )
        if getattr(viewer, "is_platform_admin", False) or getattr(viewer, "is_superadmin", False):
            return True
        return self._is_creator(gathering)

    def get_viewer_can_join(self, gathering: Gathering) -> bool:
        if self._is_creator(gathering):
            return False
        if self._joined(gathering):
            return True
        if gathering.is_cancelled:
            return False
        eligibility = self.context.get("viewer_eligibility")
        if eligibility is None:
            return False
        return bool(eligibility.get("can_join") or eligibility.get("can_create"))

    def get_viewer_unlock_hint(self, gathering: Gathering) -> str:
        if self._is_creator(gathering):
            return ""
        if self.get_viewer_can_join(gathering):
            return ""
        eligibility = self.context.get("viewer_eligibility") or {}
        required = int(eligibility.get("events_required") or 0)
        if required <= 0:
            return ""
        return (
            f"Attend {required} event{'s' if required != 1 else ''} to unlock"
        )

    def get_deletion_reason(self, gathering: Gathering) -> str:
        viewer = self._viewer()
        if viewer is None:
            return ""
        if self._is_creator(gathering) or getattr(viewer, "is_platform_admin", False) or getattr(
            viewer, "is_superadmin", False
        ):
            return gathering.deletion_reason or ""
        return ""

    def get_location_revealed(self, gathering: Gathering) -> bool:
        return viewer_can_see_location(gathering=gathering, viewer=self._viewer())

    def get_exact_location(self, gathering: Gathering) -> str:
        if viewer_can_see_location(gathering=gathering, viewer=self._viewer()):
            return gathering.exact_location
        return ""

    def get_map_link(self, gathering: Gathering) -> str:
        if viewer_can_see_location(gathering=gathering, viewer=self._viewer()):
            return gathering.map_link
        return ""


class GatheringWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Gathering
        fields = [
            "title",
            "description",
            "area",
            "exact_location",
            "map_link",
            "cover_image_key",
            "starts_at",
            "ends_at",
            "max_attendees",
        ]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        starts_at = attrs.get("starts_at", getattr(self.instance, "starts_at", None))
        ends_at = attrs.get("ends_at", getattr(self.instance, "ends_at", None))
        if starts_at is not None and ends_at is not None and ends_at <= starts_at:
            raise serializers.ValidationError("Gathering end time must be after the start time.")
        max_attendees = attrs.get("max_attendees")
        if max_attendees is not None and (max_attendees < 2 or max_attendees > GATHERING_HARD_CAP):
            raise serializers.ValidationError(
                {"max_attendees": f"Must be between 2 and {GATHERING_HARD_CAP}."}
            )
        return attrs


class GatheringDeletionRequestSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=3, max_length=2000, trim_whitespace=True)


class GatheringAttendeeSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source="user.id", read_only=True)
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = GatheringAttendee
        fields = ["user_id", "full_name", "photo_url", "joined_at"]
        read_only_fields = fields

    def get_photo_url(self, row: GatheringAttendee) -> str:
        return get_profile_photo_url(row.user)


class GatheringEligibilitySerializer(serializers.Serializer):
    can_create = serializers.BooleanField()
    can_join = serializers.BooleanField()
    events_attended = serializers.IntegerField()
    events_scanned = serializers.IntegerField()
    attendance_credit = serializers.IntegerField()
    events_required = serializers.IntegerField()
    bypass_gathering_attendance = serializers.BooleanField()
    role = serializers.CharField()
    role_label = serializers.CharField()


class GatheringCoverPresignSerializer(serializers.Serializer):
    content_type = serializers.CharField(max_length=100)
    content_length = serializers.IntegerField(min_value=1)


class GatheringCoverPresignResponseSerializer(serializers.Serializer):
    upload_url = serializers.URLField()
    object_key = serializers.CharField()
    expires_in = serializers.IntegerField()
    headers = serializers.DictField(child=serializers.CharField())


class GatheringCoverConfirmSerializer(serializers.Serializer):
    object_key = serializers.CharField(max_length=512)


class GatheringCoverConfirmResponseSerializer(serializers.Serializer):
    cover_image_url = serializers.CharField(allow_blank=True)
