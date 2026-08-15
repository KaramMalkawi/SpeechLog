from __future__ import annotations

from datetime import date
from uuid import UUID

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.authentication import VerifiedJWTAuthentication
from apps.accounts.permissions import IsIdentityVerified, IsPlatformAdmin
from apps.gatherings.exceptions import (
    GatheringAlreadyJoined,
    GatheringAtCapacity,
    GatheringCancelled,
    GatheringCommunityRequired,
    GatheringDeletionNotPending,
    GatheringCreatorCannotJoin,
    GatheringCoverError,
    GatheringEditForbidden,
    GatheringEligibilityError,
    GatheringIdentityRequired,
    GatheringNotFound,
    GatheringDeletionPending,
)
from apps.gatherings.models import Gathering
from apps.gatherings.selectors import (
    attendee_previews_for_gatherings,
    get_cover_image_url,
    get_create_eligibility,
    get_gathering_by_id,
    get_gathering_for_community,
    list_gathering_attendees,
    list_gatherings,
    list_my_created_gatherings,
    list_my_joined_gatherings,
)
from apps.gatherings.serializers import (
    GatheringAttendeeSerializer,
    GatheringDeletionRequestSerializer,
    GatheringCoverConfirmResponseSerializer,
    GatheringCoverConfirmSerializer,
    GatheringCoverPresignResponseSerializer,
    GatheringCoverPresignSerializer,
    GatheringEligibilitySerializer,
    GatheringSerializer,
    GatheringWriteSerializer,
)
from apps.gatherings.services import (
    cancel_gathering,
    confirm_gathering_cover_upload,
    create_gathering,
    create_gathering_cover_upload,
    approve_gathering_deletion,
    reject_gathering_deletion,
    request_gathering_deletion,
    join_gathering,
    remove_gathering_cover,
    resolve_community_for_request,
    update_gathering,
)
from core.pagination import CreatedAtCursorPagination, IssuedAtCursorPagination


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


def _viewer_eligibility(request) -> dict | None:
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    return get_create_eligibility(user=user)


def _serialize_gatherings(request, gatherings) -> list:
    items = list(gatherings) if not isinstance(gatherings, list) else gatherings
    previews = attendee_previews_for_gatherings(gathering_ids=[item.id for item in items])
    return GatheringSerializer(
        items,
        many=True,
        context={
            "request": request,
            "attendee_previews": previews,
            "viewer_eligibility": _viewer_eligibility(request),
        },
    ).data


def _serialize_gathering(request, gathering: Gathering) -> dict:
    previews = attendee_previews_for_gatherings(gathering_ids=[gathering.id])
    return GatheringSerializer(
        gathering,
        context={
            "request": request,
            "attendee_previews": previews,
            "viewer_eligibility": _viewer_eligibility(request),
        },
    ).data


@extend_schema_view(
    get=extend_schema(
        tags=["gatherings"],
        summary="List gatherings for a community",
        parameters=[
            OpenApiParameter(name="community_id", required=False, type=str),
            OpenApiParameter(name="city_id", required=False, type=str),
            OpenApiParameter(name="start_date", required=False, type=str),
            OpenApiParameter(name="end_date", required=False, type=str),
        ],
        responses={200: GatheringSerializer(many=True)},
    ),
    post=extend_schema(
        tags=["gatherings"],
        summary="Create a gathering",
        request=GatheringWriteSerializer,
        responses={201: GatheringSerializer},
    ),
)
class GatheringListCreateView(generics.ListCreateAPIView):
    serializer_class = GatheringSerializer
    pagination_class = CreatedAtCursorPagination
    authentication_classes = [VerifiedJWTAuthentication]

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsIdentityVerified()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return GatheringWriteSerializer
        return GatheringSerializer

    def get_queryset(self):
        community_id = _community_id_from_request(self.request)
        if community_id is None:
            raise ValidationError(
                {"community_id": "community_id query param or tenant context is required."}
            )
        return list_gatherings(
            community_id=community_id,
            city_id=_parse_optional_uuid(self.request.query_params.get("city_id")),
            start_date=_parse_optional_date(self.request.query_params.get("start_date")),
            end_date=_parse_optional_date(self.request.query_params.get("end_date")),
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            return self.get_paginated_response(_serialize_gatherings(request, page))
        return Response(_serialize_gatherings(request, queryset))

    def create(self, request, *args, **kwargs):
        serializer = GatheringWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            community = resolve_community_for_request(
                request_community=getattr(request, "community", None),
                user=request.user,
            )
            gathering = create_gathering(
                creator=request.user,
                community=community,
                **serializer.validated_data,
            )
        except GatheringCommunityRequired as exc:
            raise ValidationError({"community_id": str(exc)}) from exc
        except GatheringEligibilityError as exc:
            raise PermissionDenied(str(exc)) from exc
        except GatheringCoverError as exc:
            raise ValidationError({"cover_image_key": str(exc)}) from exc
        except GatheringEditForbidden as exc:
            raise ValidationError({"detail": str(exc)}) from exc

        gathering = get_gathering_for_community(
            gathering_id=gathering.id, community_id=community.id
        )
        return Response(_serialize_gathering(request, gathering), status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(
        tags=["gatherings"], summary="Gathering detail", responses={200: GatheringSerializer}
    ),
    patch=extend_schema(
        tags=["gatherings"],
        summary="Update gathering (creator)",
        request=GatheringWriteSerializer,
        responses={200: GatheringSerializer},
    ),
    delete=extend_schema(tags=["gatherings"], summary="Cancel gathering (creator)"),
)
class GatheringDetailView(APIView):
    authentication_classes = [VerifiedJWTAuthentication]

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsIdentityVerified()]

    def get(self, request, id: UUID):
        community_id = _community_id_from_request(request)
        if community_id is not None:
            gathering = get_gathering_for_community(gathering_id=id, community_id=community_id)
        else:
            gathering = get_gathering_by_id(gathering_id=id)
        if gathering is None:
            raise NotFound("Gathering not found.")
        return Response(_serialize_gathering(request, gathering))

    def patch(self, request, id: UUID):
        gathering = get_object_or_404(Gathering.all_objects, pk=id)
        serializer = GatheringWriteSerializer(gathering, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            updated = update_gathering(
                gathering_id=gathering.id,
                community_id=gathering.community_id,
                actor=request.user,
                **serializer.validated_data,
            )
        except GatheringNotFound as exc:
            raise NotFound(str(exc)) from exc
        except GatheringEditForbidden as exc:
            raise PermissionDenied(str(exc)) from exc
        except GatheringDeletionPending as exc:
            raise PermissionDenied(str(exc)) from exc
        except GatheringCancelled as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        except GatheringCoverError as exc:
            raise ValidationError({"cover_image_key": str(exc)}) from exc

        updated = get_gathering_for_community(
            gathering_id=updated.id, community_id=updated.community_id
        )
        return Response(_serialize_gathering(request, updated))

    def delete(self, request, id: UUID):
        gathering = get_object_or_404(Gathering.all_objects, pk=id)
        try:
            cancel_gathering(
                gathering_id=gathering.id,
                community_id=gathering.community_id,
                actor=request.user,
            )
        except GatheringNotFound as exc:
            raise NotFound(str(exc)) from exc
        except GatheringEditForbidden as exc:
            raise PermissionDenied(str(exc)) from exc
        return Response(status=status.HTTP_204_NO_CONTENT)


class GatheringDeletionRequestView(APIView):
    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsIdentityVerified]

    @extend_schema(
        tags=["gatherings"],
        summary="Request gathering deletion (creator)",
        request=GatheringDeletionRequestSerializer,
        responses={200: GatheringSerializer},
    )
    def post(self, request, gathering_id: UUID):
        community_id = _community_id_from_request(request)
        if community_id is None:
            raise ValidationError(
                {"community_id": "community_id query param or tenant context is required."}
            )

        serializer = GatheringDeletionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated = request_gathering_deletion(
                gathering_id=gathering_id,
                community_id=community_id,
                actor=request.user,
                reason=serializer.validated_data["reason"],
            )
        except GatheringNotFound as exc:
            raise NotFound(str(exc)) from exc
        except GatheringDeletionPending as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        except GatheringEditForbidden as exc:
            raise PermissionDenied(str(exc)) from exc
        return Response(_serialize_gathering(request, updated))


class GatheringDeletionApproveView(APIView):
    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsPlatformAdmin]

    @extend_schema(
        tags=["gatherings"],
        summary="Approve pending gathering deletion (admin)",
        responses={200: GatheringSerializer},
    )
    def post(self, request, gathering_id: UUID):
        gathering = get_object_or_404(Gathering.all_objects, pk=gathering_id)
        try:
            updated = approve_gathering_deletion(
                gathering_id=gathering.id,
                community_id=gathering.community_id,
                actor=request.user,
            )
        except GatheringNotFound as exc:
            raise NotFound(str(exc)) from exc
        except GatheringDeletionNotPending as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        except GatheringEditForbidden as exc:
            raise PermissionDenied(str(exc)) from exc
        return Response(_serialize_gathering(request, updated))


class GatheringDeletionRejectView(APIView):
    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsPlatformAdmin]

    @extend_schema(
        tags=["gatherings"],
        summary="Reject pending gathering deletion (admin)",
        responses={200: GatheringSerializer},
    )
    def post(self, request, gathering_id: UUID):
        gathering = get_object_or_404(Gathering.all_objects, pk=gathering_id)
        try:
            updated = reject_gathering_deletion(
                gathering_id=gathering.id,
                community_id=gathering.community_id,
                actor=request.user,
            )
        except GatheringNotFound as exc:
            raise NotFound(str(exc)) from exc
        except GatheringDeletionNotPending as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        except GatheringEditForbidden as exc:
            raise PermissionDenied(str(exc)) from exc
        return Response(_serialize_gathering(request, updated))


class GatheringJoinView(APIView):
    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsIdentityVerified]

    @extend_schema(
        tags=["gatherings"],
        summary="Join a gathering",
        responses={201: GatheringAttendeeSerializer},
    )
    def post(self, request, gathering_id: UUID):
        community_id = _community_id_from_request(request)
        if community_id is None:
            raise ValidationError({"community_id": "community_id query param or tenant context is required."})
        try:
            attendee = join_gathering(
                gathering_id=gathering_id,
                community_id=community_id,
                user=request.user,
            )
        except GatheringNotFound as exc:
            raise NotFound(str(exc)) from exc
        except GatheringIdentityRequired as exc:
            return Response(
                {
                    "detail": str(exc),
                    "code": "identity_verification_required",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        except GatheringEligibilityError as exc:
            raise PermissionDenied(str(exc)) from exc
        except (
            GatheringCancelled,
            GatheringAlreadyJoined,
            GatheringAtCapacity,
            GatheringCreatorCannotJoin,
        ) as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        return Response(
            GatheringAttendeeSerializer(attendee).data,
            status=status.HTTP_201_CREATED,
        )


class GatheringAttendeeListView(generics.ListAPIView):
    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsIdentityVerified]
    serializer_class = GatheringAttendeeSerializer
    pagination_class = IssuedAtCursorPagination

    @extend_schema(tags=["gatherings"], summary="List gathering attendees")
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        gathering = get_object_or_404(Gathering.all_objects, pk=self.kwargs["gathering_id"])
        return list_gathering_attendees(
            gathering_id=gathering.id, community_id=gathering.community_id
        )


class MyGatheringsView(generics.ListAPIView):
    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsIdentityVerified]
    pagination_class = CreatedAtCursorPagination

    @extend_schema(
        tags=["gatherings"],
        summary="List gatherings I created or joined",
        parameters=[
            OpenApiParameter(
                name="scope",
                required=False,
                type=str,
                description="created | joined (default: joined)",
            ),
        ],
    )
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        scope = str(self.request.query_params.get("scope") or "joined").strip().lower()
        user_id = self.request.user.id
        if scope == "created":
            return list_my_created_gatherings(user_id=user_id)
        return list_my_joined_gatherings(user_id=user_id)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            return self.get_paginated_response(_serialize_gatherings(request, page))
        return Response(_serialize_gatherings(request, queryset))


class GatheringEligibilityView(APIView):
    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsIdentityVerified]

    @extend_schema(
        tags=["gatherings"],
        summary="Check create/join eligibility for gatherings",
        responses={200: GatheringEligibilitySerializer},
    )
    def get(self, request):
        return Response(get_create_eligibility(user=request.user))


class GatheringCoverPresignView(APIView):
    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsIdentityVerified]

    @extend_schema(
        tags=["gatherings"],
        summary="Presign S3 upload for a gathering cover",
        request=GatheringCoverPresignSerializer,
        responses={201: GatheringCoverPresignResponseSerializer},
    )
    def post(self, request):
        serializer = GatheringCoverPresignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            presigned = create_gathering_cover_upload(
                uploader=request.user,
                content_type=serializer.validated_data["content_type"],
                content_length=serializer.validated_data["content_length"],
            )
        except GatheringCoverError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        return Response(presigned, status=status.HTTP_201_CREATED)


class GatheringCoverConfirmView(APIView):
    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsIdentityVerified]

    @extend_schema(
        tags=["gatherings"],
        summary="Confirm uploaded gathering cover",
        request=GatheringCoverConfirmSerializer,
        responses={200: GatheringCoverConfirmResponseSerializer},
    )
    def post(self, request, gathering_id: UUID):
        gathering = get_object_or_404(Gathering.all_objects, pk=gathering_id)
        if gathering.is_cancelled:
            raise PermissionDenied("This gathering has been cancelled.")
        if gathering.deletion_status == Gathering.DeletionStatus.APPROVED:
            raise PermissionDenied("This gathering has been deleted.")
        if (
            gathering.deletion_status == Gathering.DeletionStatus.PENDING
            and not (request.user.is_platform_admin or request.user.is_superadmin)
        ):
            raise PermissionDenied(
                "This gathering has a pending deletion request and cannot be edited."
            )
        if gathering.creator_id != request.user.id and not request.user.is_platform_admin:
            raise PermissionDenied("Only the creator can update the cover.")
        serializer = GatheringCoverConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            updated = confirm_gathering_cover_upload(
                gathering_id=gathering.id,
                community_id=gathering.community_id,
                object_key=serializer.validated_data["object_key"],
            )
        except GatheringNotFound as exc:
            raise NotFound(str(exc)) from exc
        except GatheringCoverError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        return Response({"cover_image_url": get_cover_image_url(updated)})


class GatheringCoverDeleteView(APIView):
    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsIdentityVerified]

    @extend_schema(tags=["gatherings"], summary="Remove gathering cover")
    def delete(self, request, gathering_id: UUID):
        gathering = get_object_or_404(Gathering.all_objects, pk=gathering_id)
        if gathering.is_cancelled:
            raise PermissionDenied("This gathering has been cancelled.")
        if gathering.deletion_status == Gathering.DeletionStatus.APPROVED:
            raise PermissionDenied("This gathering has been deleted.")
        if (
            gathering.deletion_status == Gathering.DeletionStatus.PENDING
            and not (request.user.is_platform_admin or request.user.is_superadmin)
        ):
            raise PermissionDenied(
                "This gathering has a pending deletion request and cannot be edited."
            )
        if gathering.creator_id != request.user.id and not request.user.is_platform_admin:
            raise PermissionDenied("Only the creator can remove the cover.")
        try:
            remove_gathering_cover(gathering_id=gathering.id, community_id=gathering.community_id)
        except GatheringNotFound as exc:
            raise NotFound(str(exc)) from exc
        except GatheringCoverError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        return Response(status=status.HTTP_204_NO_CONTENT)
