from django.urls import path

from apps.gatherings.views import (
    GatheringAttendeeListView,
    GatheringDeletionApproveView,
    GatheringDeletionRejectView,
    GatheringDeletionRequestView,
    GatheringCoverConfirmView,
    GatheringCoverDeleteView,
    GatheringCoverPresignView,
    GatheringDetailView,
    GatheringEligibilityView,
    GatheringJoinView,
    GatheringListCreateView,
    MyGatheringsView,
)

urlpatterns = [
    path("", GatheringListCreateView.as_view(), name="gathering-list-create"),
    path("my/", MyGatheringsView.as_view(), name="gathering-my"),
    path("eligibility/", GatheringEligibilityView.as_view(), name="gathering-eligibility"),
    path("covers/presign/", GatheringCoverPresignView.as_view(), name="gathering-cover-presign"),
    path("<uuid:id>/", GatheringDetailView.as_view(), name="gathering-detail"),
    path("<uuid:gathering_id>/join/", GatheringJoinView.as_view(), name="gathering-join"),
    path(
        "<uuid:gathering_id>/deletion/request/",
        GatheringDeletionRequestView.as_view(),
        name="gathering-deletion-request",
    ),
    path(
        "<uuid:gathering_id>/deletion/approve/",
        GatheringDeletionApproveView.as_view(),
        name="gathering-deletion-approve",
    ),
    path(
        "<uuid:gathering_id>/deletion/reject/",
        GatheringDeletionRejectView.as_view(),
        name="gathering-deletion-reject",
    ),
    path(
        "<uuid:gathering_id>/cover/confirm/",
        GatheringCoverConfirmView.as_view(),
        name="gathering-cover-confirm",
    ),
    path(
        "<uuid:gathering_id>/cover/",
        GatheringCoverDeleteView.as_view(),
        name="gathering-cover-delete",
    ),
    path(
        "<uuid:gathering_id>/attendees/",
        GatheringAttendeeListView.as_view(),
        name="gathering-attendee-list",
    ),
]
