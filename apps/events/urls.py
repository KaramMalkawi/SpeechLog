from django.urls import path

from apps.events.views import (
    EventAttendeeListView,
    EventCoverConfirmView,
    EventCoverDeleteView,
    EventCoverPresignView,
    EventDetailView,
    EventJoinRequestAcceptView,
    EventJoinRequestListView,
    EventJoinRequestRejectView,
    EventJoinView,
    EventListCreateView,
    MyTicketsView,
    TicketCheckView,
)

urlpatterns = [
    path("", EventListCreateView.as_view(), name="event-list-create"),
    path("my-tickets/", MyTicketsView.as_view(), name="event-my-tickets"),
    path("covers/presign/", EventCoverPresignView.as_view(), name="event-cover-presign"),
    path("tickets/check/", TicketCheckView.as_view(), name="event-ticket-check"),
    path("<uuid:id>/", EventDetailView.as_view(), name="event-detail"),
    path("<uuid:event_id>/join/", EventJoinView.as_view(), name="event-join"),
    path(
        "<uuid:event_id>/cover/confirm/",
        EventCoverConfirmView.as_view(),
        name="event-cover-confirm",
    ),
    path(
        "<uuid:event_id>/cover/",
        EventCoverDeleteView.as_view(),
        name="event-cover-delete",
    ),
    path(
        "<uuid:event_id>/requests/",
        EventJoinRequestListView.as_view(),
        name="event-join-request-list",
    ),
    path(
        "<uuid:event_id>/requests/<uuid:request_id>/accept/",
        EventJoinRequestAcceptView.as_view(),
        name="event-join-request-accept",
    ),
    path(
        "<uuid:event_id>/requests/<uuid:request_id>/reject/",
        EventJoinRequestRejectView.as_view(),
        name="event-join-request-reject",
    ),
    path(
        "<uuid:event_id>/attendees/",
        EventAttendeeListView.as_view(),
        name="event-attendee-list",
    ),
]
