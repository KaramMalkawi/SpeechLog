from __future__ import annotations

from datetime import date
from uuid import UUID

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.authentication import VerifiedJWTAuthentication
from apps.accounts.permissions import (
    CommunityFounderOnlyPermission,
    IsCityFounder,
    IsIdentityVerified,
)
from apps.accounts.role_checks import user_is_community_city_founder
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
from apps.events.models import Event
from apps.events.selectors import (
    attendee_previews_for_events,
    get_cover_image_url,
    get_event_by_id,
    get_event_for_community,
    list_event_attendees,
    list_events,
    list_my_tickets,
    list_pending_join_requests,
)
from apps.events.serializers import (
    EventAttendeePublicSerializer,
    EventAttendeeSerializer,
    EventCoverConfirmResponseSerializer,
    EventCoverConfirmSerializer,
    EventCoverPresignResponseSerializer,
    EventCoverPresignSerializer,
    EventJoinRequestSerializer,
    EventSerializer,
    EventTicketSerializer,
    EventWriteSerializer,
    TicketCheckSerializer,
)
from apps.events.services import (
    confirm_event_cover_upload,
    create_event,
    create_event_cover_upload,
    delete_event,
    fulfill_approved_join_for_event,
    fulfill_approved_joins_for_user,
    join_event,
    remove_event_cover,
    resolve_community_for_request,
    respond_to_join_request,
    update_event,
    verify_ticket_token,
    mark_ticket_scanned,
    TicketScanError,
)
from core.pagination import (
    IssuedAtCursorPagination,
    RequestedAtCursorPagination,
    StartsAtCursorPagination,
)


def _parse_optional_uuid(raw: str | None) -> UUID | None:
    if not raw:
        return None
    try:
        return UUID(raw)
    except ValueError as exc:
        raise ValidationError({"detail": "Invalid UUID."}) from exc


def _parse_optional_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValidationError({"detail": "Invalid date. Use YYYY-MM-DD."}) from exc


def _community_id_from_request(request) -> UUID | None:
    query_community_id = _parse_optional_uuid(request.query_params.get("community_id"))
    if query_community_id is not None:
        return query_community_id

    community = getattr(request, "community", None)
    if community is not None:
        return community.id

    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False) and user.active_community_id:
        return user.active_community_id
    return None


def _serialize_events(request, events) -> list | dict:
    event_list = list(events) if not isinstance(events, list) else events
    previews = attendee_previews_for_events(event_ids=[event.id for event in event_list])
    return EventSerializer(
        event_list,
        many=True,
        context={"request": request, "attendee_previews": previews},
    ).data


def _serialize_event(request, event: Event) -> dict:
    previews = attendee_previews_for_events(event_ids=[event.id])
    return EventSerializer(
        event,
        context={"request": request, "attendee_previews": previews},
    ).data


@extend_schema_view(
    get=extend_schema(
        tags=["events"],
        summary="List events for a community",
        parameters=[
            OpenApiParameter(name="community_id", required=False, type=str),
            OpenApiParameter(name="city_id", required=False, type=str),
            OpenApiParameter(name="category", required=False, type=str),
            OpenApiParameter(name="start_date", required=False, type=str),
            OpenApiParameter(name="end_date", required=False, type=str),
        ],
        responses={200: EventSerializer(many=True)},
    ),
    post=extend_schema(
        tags=["events"],
        summary="Create an event (City Founder)",
        request=EventWriteSerializer,
        responses={201: EventSerializer},
    ),
)
class EventListCreateView(generics.ListCreateAPIView):
    serializer_class = EventSerializer
    pagination_class = StartsAtCursorPagination
    authentication_classes = [VerifiedJWTAuthentication]

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsIdentityVerified(), IsCityFounder()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return EventWriteSerializer
        return EventSerializer

    def get_queryset(self):
        community_id = _community_id_from_request(self.request)
        if community_id is None:
            raise ValidationError(
                {"community_id": "community_id query param or tenant context is required."}
            )
        return list_events(
            community_id=community_id,
            city_id=_parse_optional_uuid(self.request.query_params.get("city_id")),
            category=self.request.query_params.get("category") or None,
            start_date=_parse_optional_date(self.request.query_params.get("start_date")),
            end_date=_parse_optional_date(self.request.query_params.get("end_date")),
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            return self.get_paginated_response(_serialize_events(request, page))
        return Response(_serialize_events(request, queryset))

    def create(self, request, *args, **kwargs):
        serializer = EventWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            community = resolve_community_for_request(
                request_community=getattr(request, "community", None),
                user=request.user,
            )
        except EventCommunityRequired as exc:
            raise ValidationError({"community_id": str(exc)}) from exc

        try:
            event = create_event(
                creator=request.user,
                community=community,
                **serializer.validated_data,
            )
        except EventCoverError as exc:
            raise ValidationError({"cover_image_key": str(exc)}) from exc

        event = get_event_for_community(event_id=event.id, community_id=community.id)
        return Response(_serialize_event(request, event), status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(tags=["events"], summary="Event detail", responses={200: EventSerializer}),
    patch=extend_schema(
        tags=["events"],
        summary="Update event (City Founder)",
        request=EventWriteSerializer,
        responses={200: EventSerializer},
    ),
    delete=extend_schema(tags=["events"], summary="Cancel/delete event (City Founder)"),
)
class EventDetailView(APIView):
    authentication_classes = [VerifiedJWTAuthentication]

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsIdentityVerified(), CommunityFounderOnlyPermission()]

    def get(self, request, id: UUID):
        community_id = _community_id_from_request(request)
        if community_id is not None:
            event = get_event_for_community(event_id=id, community_id=community_id)
        else:
            event = get_event_by_id(event_id=id)
        if event is None:
            raise NotFound("Event not found.")
        if getattr(request.user, "is_authenticated", False):
            fulfill_approved_join_for_event(event=event, user=request.user)
            # Re-fetch so attendee_count / viewer_join_status reflect a new ticket.
            if community_id is not None:
                event = get_event_for_community(event_id=id, community_id=community_id)
            else:
                event = get_event_by_id(event_id=id)
        return Response(_serialize_event(request, event))

    def patch(self, request, id: UUID):
        event = get_object_or_404(Event.all_objects, pk=id)
        self.check_object_permissions(request, event)

        serializer = EventWriteSerializer(event, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            updated = update_event(
                event_id=event.id,
                community_id=event.community_id,
                **serializer.validated_data,
            )
        except EventEditForbidden as exc:
            field = (
                "price"
                if "Price" in str(exc)
                else "location" if "Location" in str(exc) else "detail"
            )
            raise ValidationError({field: str(exc)}) from exc
        except EventCoverError as exc:
            raise ValidationError({"cover_image_key": str(exc)}) from exc
        except EventNotFound as exc:
            raise NotFound(str(exc)) from exc

        updated = get_event_for_community(event_id=updated.id, community_id=updated.community_id)
        return Response(_serialize_event(request, updated))

    def delete(self, request, id: UUID):
        event = get_object_or_404(Event.all_objects, pk=id)
        self.check_object_permissions(request, event)
        try:
            delete_event(event_id=event.id, community_id=event.community_id)
        except EventNotFound as exc:
            raise NotFound(str(exc)) from exc
        return Response(status=status.HTTP_204_NO_CONTENT)


class EventJoinView(APIView):
    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsIdentityVerified]

    @extend_schema(
        tags=["events"],
        summary="Join or request a ticket for an event",
        responses={201: EventTicketSerializer, 200: EventJoinRequestSerializer},
    )
    def post(self, request, event_id: UUID):
        try:
            kind, result = join_event(event_id=event_id, user=request.user)
        except EventNotFound as exc:
            raise NotFound(str(exc)) from exc
        except EventIdentityRequired as exc:
            return Response(
                {
                    "detail": str(exc),
                    "code": "identity_verification_required",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        except (EventCancelled, EventAlreadyJoined, EventAtCapacity) as exc:
            raise ValidationError({"detail": str(exc)}) from exc

        if kind == "ticket":
            return Response(EventTicketSerializer(result).data, status=status.HTTP_201_CREATED)
        return Response(EventJoinRequestSerializer(result).data, status=status.HTTP_201_CREATED)


class EventJoinRequestListView(generics.ListAPIView):
    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsIdentityVerified, CommunityFounderOnlyPermission]
    serializer_class = EventJoinRequestSerializer
    pagination_class = RequestedAtCursorPagination

    @extend_schema(tags=["events"], summary="List pending join requests")
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        event = get_object_or_404(Event.all_objects, pk=self.kwargs["event_id"])
        self.check_object_permissions(self.request, event)
        return list_pending_join_requests(event_id=event.id, community_id=event.community_id)


class EventJoinRequestActionView(APIView):
    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsIdentityVerified, CommunityFounderOnlyPermission]
    approve = False

    def post(self, request, event_id: UUID, request_id: UUID):
        event = get_object_or_404(Event.all_objects, pk=event_id)
        self.check_object_permissions(request, event)
        try:
            join_request = respond_to_join_request(
                event_id=event_id,
                request_id=request_id,
                community_id=event.community_id,
                approve=self.approve,
            )
        except JoinRequestNotFound as exc:
            raise NotFound(str(exc)) from exc
        except JoinRequestNotPending as exc:
            raise ValidationError({"detail": str(exc)}) from exc

        return Response(EventJoinRequestSerializer(join_request).data)


@extend_schema(tags=["events"], summary="Accept join request")
class EventJoinRequestAcceptView(EventJoinRequestActionView):
    approve = True


@extend_schema(tags=["events"], summary="Reject join request")
class EventJoinRequestRejectView(EventJoinRequestActionView):
    approve = False


class EventAttendeeListView(generics.ListAPIView):
    """Public attendee 'see all' for verified users; founders get richer fields."""

    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsIdentityVerified]
    pagination_class = IssuedAtCursorPagination

    def get_serializer_class(self):
        event = getattr(self, "_event", None)
        user = self.request.user
        if event is not None and user_is_community_city_founder(user, event.community_id):
            return EventAttendeeSerializer
        return EventAttendeePublicSerializer

    @extend_schema(tags=["events"], summary="List event attendees")
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        event = get_object_or_404(Event.all_objects, pk=self.kwargs["event_id"])
        self._event = event
        return list_event_attendees(event_id=event.id, community_id=event.community_id)


class MyTicketsView(generics.ListAPIView):
    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsIdentityVerified]
    serializer_class = EventTicketSerializer
    pagination_class = IssuedAtCursorPagination

    @extend_schema(tags=["events"], summary="List my tickets")
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        fulfill_approved_joins_for_user(user_id=self.request.user.id)
        return list_my_tickets(user_id=self.request.user.id)


class TicketCheckView(APIView):
    """Check (scan) an event ticket by QR token.

    Expects a JSON body with `token` containing the signed ticket token embedded
    in the QR code. Marks the ticket as scanned and returns the ticket payload.
    """

    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsIdentityVerified, CommunityFounderOnlyPermission]

    @extend_schema(
        tags=["events"],
        summary="Check (scan) an event ticket by QR token",
        request=TicketCheckSerializer,
        responses={200: EventTicketSerializer},
    )
    def post(self, request):
        serializer = TicketCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]

        # Verify the token is a valid signed payload (raises on failure)
        try:
            verify_ticket_token(token)
        except Exception as exc:
            raise ValidationError({"token": "Invalid or expired ticket token."}) from exc

        # Locate the ticket and mark it scanned
        ticket = EventTicket.all_objects.filter(token=token).first()
        if ticket is None:
            raise NotFound("Ticket not found.")
        try:
            checked = mark_ticket_scanned(ticket_id=ticket.id)
        except TicketScanError as exc:
            raise ValidationError({"detail": str(exc)}) from exc

        return Response(EventTicketSerializer(checked, context={"request": request}).data)


class EventCoverPresignView(APIView):
    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsIdentityVerified, IsCityFounder]

    @extend_schema(
        tags=["events"],
        summary="Presign S3 upload for an event cover image",
        request=EventCoverPresignSerializer,
        responses={201: EventCoverPresignResponseSerializer},
    )
    def post(self, request):
        serializer = EventCoverPresignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            presigned = create_event_cover_upload(
                uploader=request.user,
                content_type=serializer.validated_data["content_type"],
                content_length=serializer.validated_data["content_length"],
            )
        except EventCoverError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        return Response(presigned, status=status.HTTP_201_CREATED)


class EventCoverConfirmView(APIView):
    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsIdentityVerified, CommunityFounderOnlyPermission]

    @extend_schema(
        tags=["events"],
        summary="Confirm uploaded cover image for an event",
        request=EventCoverConfirmSerializer,
        responses={200: EventCoverConfirmResponseSerializer},
    )
    def post(self, request, event_id: UUID):
        event = get_object_or_404(Event.all_objects, pk=event_id)
        self.check_object_permissions(request, event)
        serializer = EventCoverConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            updated = confirm_event_cover_upload(
                event_id=event.id,
                community_id=event.community_id,
                object_key=serializer.validated_data["object_key"],
            )
        except EventNotFound as exc:
            raise NotFound(str(exc)) from exc
        except EventCoverError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        return Response({"cover_image_url": get_cover_image_url(updated)})


class EventCoverDeleteView(APIView):
    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsIdentityVerified, CommunityFounderOnlyPermission]

    @extend_schema(tags=["events"], summary="Remove event cover image")
    def delete(self, request, event_id: UUID):
        event = get_object_or_404(Event.all_objects, pk=event_id)
        self.check_object_permissions(request, event)
        try:
            remove_event_cover(event_id=event.id, community_id=event.community_id)
        except EventNotFound as exc:
            raise NotFound(str(exc)) from exc
        except EventCoverError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        return Response(status=status.HTTP_204_NO_CONTENT)
