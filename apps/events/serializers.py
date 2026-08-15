from __future__ import annotations

from typing import Any

from rest_framework import serializers

from apps.accounts.models import User
from apps.events.models import Event, EventJoinRequest, EventTicket
from apps.events.selectors import (
    build_organizer_payload,
    get_cover_image_url,
    get_viewer_join_status,
    spots_left_for_event,
    viewer_requires_approval,
)
from apps.events.services import event_nationality_breakdown


class EventOrganizerSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    full_name = serializers.CharField()
    photo_url = serializers.CharField(allow_blank=True)
    role = serializers.CharField()
    role_label = serializers.CharField()


class EventAttendeePreviewSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    full_name = serializers.CharField()
    photo_url = serializers.CharField(allow_blank=True)


class EventSerializer(serializers.ModelSerializer):
    creator_id = serializers.UUIDField(read_only=True)
    creator_full_name = serializers.CharField(source="creator.full_name", read_only=True)
    cover_image_url = serializers.SerializerMethodField()
    attendee_count = serializers.IntegerField(read_only=True)
    attendee_previews = serializers.SerializerMethodField()
    attendee_extra_count = serializers.SerializerMethodField()
    spots_total = serializers.IntegerField(source="capacity", read_only=True, allow_null=True)
    spots_left = serializers.SerializerMethodField()
    organizer = serializers.SerializerMethodField()
    viewer_join_status = serializers.SerializerMethodField()
    requires_approval = serializers.SerializerMethodField()
    nationality_breakdown = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "description",
            "location",
            "cover_image_url",
            "starts_at",
            "ends_at",
            "price",
            "currency",
            "category",
            "capacity",
            "spots_total",
            "spots_left",
            "is_cancelled",
            "creator_id",
            "creator_full_name",
            "organizer",
            "community_id",
            "city_id",
            "attendee_count",
            "attendee_previews",
            "attendee_extra_count",
            "viewer_join_status",
            "requires_approval",
            "nationality_breakdown",
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

    def _attendee_count(self, event: Event) -> int:
        return int(getattr(event, "attendee_count", 0) or 0)

    def get_cover_image_url(self, event: Event) -> str:
        return get_cover_image_url(event)

    def get_attendee_previews(self, event: Event) -> list[dict]:
        previews_map = self.context.get("attendee_previews") or {}
        return previews_map.get(event.id, [])

    def get_attendee_extra_count(self, event: Event) -> int:
        previews = self.get_attendee_previews(event)
        return max(self._attendee_count(event) - len(previews), 0)

    def get_spots_left(self, event: Event) -> int | None:
        return spots_left_for_event(event=event, attendee_count=self._attendee_count(event))

    def get_organizer(self, event: Event) -> dict:
        return build_organizer_payload(creator=event.creator, city_id=event.city_id)

    def get_viewer_join_status(self, event: Event) -> str:
        return get_viewer_join_status(event=event, viewer=self._viewer())

    def get_requires_approval(self, event: Event) -> bool:
        return viewer_requires_approval(viewer=self._viewer())

    def get_nationality_breakdown(self, event: Event) -> dict[str, int]:
        return event_nationality_breakdown(event)


class EventWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = [
            "title",
            "description",
            "location",
            "cover_image_key",
            "starts_at",
            "ends_at",
            "price",
            "currency",
            "category",
            "capacity",
            "is_cancelled",
        ]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        starts_at = attrs.get("starts_at", getattr(self.instance, "starts_at", None))
        ends_at = attrs.get("ends_at", getattr(self.instance, "ends_at", None))
        if starts_at is not None and ends_at is not None and ends_at <= starts_at:
            raise serializers.ValidationError("Event end time must be after the start time.")
        currency = attrs.get("currency")
        if currency is not None:
            attrs["currency"] = str(currency).upper()
        return attrs


class EventJoinRequestSerializer(serializers.ModelSerializer):
    user_full_name = serializers.CharField(source="user.full_name", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = EventJoinRequest
        fields = [
            "id",
            "event",
            "user",
            "user_full_name",
            "user_email",
            "status",
            "requested_at",
            "responded_at",
            "notes",
        ]
        read_only_fields = fields


class EventTicketSerializer(serializers.ModelSerializer):
    event_title = serializers.CharField(source="event.title", read_only=True)
    event_starts_at = serializers.DateTimeField(source="event.starts_at", read_only=True)
    event_location = serializers.CharField(source="event.location", read_only=True)
    event_is_cancelled = serializers.BooleanField(source="event.is_cancelled", read_only=True)

    class Meta:
        model = EventTicket
        fields = [
            "id",
            "event",
            "event_title",
            "event_starts_at",
            "event_location",
            "event_is_cancelled",
            "token",
            "issued_at",
            "is_active",
        ]
        read_only_fields = fields


class TicketCheckSerializer(serializers.Serializer):
    """Input serializer for ticket checks (QR payload)."""

    token = serializers.CharField(max_length=1024)


class EventAttendeeSerializer(serializers.ModelSerializer):
    """Founder-facing attendee row with contact + nationality."""

    user_full_name = serializers.CharField(source="user.full_name", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)
    nationality_code = serializers.CharField(source="user.nationality_code", read_only=True)
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = EventTicket
        fields = [
            "id",
            "user",
            "user_full_name",
            "user_email",
            "nationality_code",
            "photo_url",
            "issued_at",
        ]
        read_only_fields = fields

    def get_photo_url(self, ticket: EventTicket) -> str:
        from apps.accounts.profile_selectors import get_profile_photo_url

        return get_profile_photo_url(ticket.user)


class EventAttendeePublicSerializer(serializers.ModelSerializer):
    """Public/member-facing attendee row for Explore 'see all'."""

    user_id = serializers.UUIDField(source="user.id", read_only=True)
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = EventTicket
        fields = ["user_id", "full_name", "photo_url", "issued_at"]
        read_only_fields = fields

    def get_photo_url(self, ticket: EventTicket) -> str:
        from apps.accounts.profile_selectors import get_profile_photo_url

        return get_profile_photo_url(ticket.user)


class EventCoverPresignSerializer(serializers.Serializer):
    content_type = serializers.CharField(max_length=100)
    content_length = serializers.IntegerField(min_value=1)


class EventCoverPresignResponseSerializer(serializers.Serializer):
    upload_url = serializers.URLField()
    object_key = serializers.CharField()
    expires_in = serializers.IntegerField()
    headers = serializers.DictField(child=serializers.CharField())


class EventCoverConfirmSerializer(serializers.Serializer):
    object_key = serializers.CharField(max_length=512)


class EventCoverConfirmResponseSerializer(serializers.Serializer):
    cover_image_url = serializers.CharField(allow_blank=True)
