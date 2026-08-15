from __future__ import annotations

from django.conf import settings
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.authentication import VerifiedJWTAuthentication
from apps.accounts.permissions import FounderPasswordChanged, IsCityFounder, IsPlatformAdmin
from apps.founders.applications import (
    FounderApplicationNotFound,
    FounderApplicationSyncError,
    founder_application_to_payload,
    get_or_create_sync_state,
    sync_founder_applications_from_sheet,
    sync_state_to_payload,
    update_founder_application_status,
)
from apps.founders.selectors import (
    get_city_founder_by_id,
    get_founder_application_by_id,
    list_city_founders,
    list_founder_applications,
)
from apps.founders.serializers import (
    CityFounderCreateSerializer,
    CityFounderDeleteSerializer,
    CityFounderSerializer,
    CityFounderUpdateSerializer,
    FounderApplicationSerializer,
    FounderApplicationStatusUpdateSerializer,
    FounderApplicationSyncResultSerializer,
    FounderApplicationSyncStateSerializer,
    FounderChangePasswordSerializer,
    FounderDashboardOverviewSerializer,
)
from apps.founders.services import (
    CityFounderDeleteConfirmationError,
    CityFounderNotFound,
    city_founder_to_payload,
    create_city_founder,
    delete_city_founder,
    get_founder_dashboard_overview,
    update_city_founder,
)
from apps.founders.tasks import send_city_founder_invite_email_task
from apps.tenancy.selectors import get_city_by_id


class CityFounderListCreateView(APIView):
    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsPlatformAdmin]

    @extend_schema(
        tags=["founders"],
        summary="List city founders",
        parameters=[
            OpenApiParameter(name="status", required=False, type=str),
            OpenApiParameter(name="search", required=False, type=str),
        ],
        responses={200: CityFounderSerializer(many=True)},
    )
    def get(self, request):
        founders = list_city_founders(
            status=request.query_params.get("status") or None,
            search=request.query_params.get("search") or None,
        )
        payload = [
            city_founder_to_payload(founder, city=get_city_by_id(founder.city_id))
            for founder in founders
        ]
        return Response(CityFounderSerializer(payload, many=True).data)

    @extend_schema(
        tags=["founders"],
        summary="Create city founder",
        description=(
            "Creates a City Founder user (role=city_founder), assigns them to a city, "
            "and emails a temporary password via Resend."
        ),
        request=CityFounderCreateSerializer,
        responses={201: CityFounderSerializer},
    )
    def post(self, request):
        serializer = CityFounderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        founder, temporary_password = create_city_founder(
            actor_id=request.user.id,
            full_name=data["full_name"],
            email=data["email"],
            city_id=data["city_id"],
        )
        city = get_city_by_id(founder.city_id)
        send_city_founder_invite_email_task.delay(
            to=founder.user.email,
            temporary_password=temporary_password,
            recipient_name=founder.user.full_name,
            city_name=city.name if city else "",
            country_name=city.country.name if city else "",
            login_url=settings.EMAIL_BRAND_WEBSITE.rstrip("/"),
        )
        return Response(
            CityFounderSerializer(city_founder_to_payload(founder, city=city)).data,
            status=status.HTTP_201_CREATED,
        )


class CityFounderDetailView(APIView):
    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsPlatformAdmin]

    @extend_schema(
        tags=["founders"],
        summary="Get city founder",
        responses={200: CityFounderSerializer},
    )
    def get(self, request, founder_id):
        founder = get_city_founder_by_id(founder_id)
        if founder is None:
            return Response({"detail": "City founder not found."}, status=status.HTTP_404_NOT_FOUND)
        city = get_city_by_id(founder.city_id)
        return Response(CityFounderSerializer(city_founder_to_payload(founder, city=city)).data)

    @extend_schema(
        tags=["founders"],
        summary="Update city founder",
        request=CityFounderUpdateSerializer,
        responses={200: CityFounderSerializer},
    )
    def patch(self, request, founder_id):
        serializer = CityFounderUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            founder = update_city_founder(
                actor_id=request.user.id,
                founder_id=founder_id,
                **serializer.validated_data,
            )
        except CityFounderNotFound:
            return Response({"detail": "City founder not found."}, status=status.HTTP_404_NOT_FOUND)

        city = get_city_by_id(founder.city_id)
        return Response(CityFounderSerializer(city_founder_to_payload(founder, city=city)).data)

    @extend_schema(
        tags=["founders"],
        summary="Delete city founder",
        description=(
            "Permanently deletes the City Founder account. "
            "Requires typing their full name."
        ),
        request=CityFounderDeleteSerializer,
        responses={204: None},
    )
    def delete(self, request, founder_id):
        serializer = CityFounderDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            delete_city_founder(
                actor_id=request.user.id,
                founder_id=founder_id,
                confirmation_name=serializer.validated_data["confirmation_name"],
            )
        except CityFounderNotFound:
            return Response({"detail": "City founder not found."}, status=status.HTTP_404_NOT_FOUND)
        except CityFounderDeleteConfirmationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class FounderDashboardOverviewView(APIView):
    """City Founder overview — role-gated; not available to Members/Non-Members."""

    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsCityFounder, FounderPasswordChanged]

    @extend_schema(
        tags=["founders"],
        summary="City Founder dashboard overview",
        responses={200: FounderDashboardOverviewSerializer},
    )
    def get(self, request):
        try:
            payload = get_founder_dashboard_overview(user_id=request.user.id)
        except CityFounderNotFound:
            return Response(
                {"detail": "City founder profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(FounderDashboardOverviewSerializer(payload).data)


class FounderChangePasswordView(APIView):
    """City Founder must change temporary password on first dashboard login."""

    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsCityFounder]

    @extend_schema(
        tags=["founders"],
        summary="Change City Founder password",
        request=FounderChangePasswordSerializer,
        responses={200: FounderDashboardOverviewSerializer},
    )
    def post(self, request):
        from apps.accounts.services import change_founder_password

        serializer = FounderChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            change_founder_password(
                user_id=request.user.id,
                current_password=serializer.validated_data["current_password"],
                new_password=serializer.validated_data["new_password"],
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payload = get_founder_dashboard_overview(user_id=request.user.id)
        except CityFounderNotFound:
            return Response(
                {"detail": "City founder profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(FounderDashboardOverviewSerializer(payload).data)


class FounderApplicationListView(APIView):
    """List cached City Founder applications (served from DB, not live Sheets)."""

    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsPlatformAdmin]

    @extend_schema(
        tags=["founders"],
        summary="List City Founder applications",
        parameters=[
            OpenApiParameter(name="status", required=False, type=str),
            OpenApiParameter(name="search", required=False, type=str),
        ],
        responses={200: FounderApplicationSerializer(many=True)},
    )
    def get(self, request):
        applications = list_founder_applications(
            status=request.query_params.get("status") or None,
            search=request.query_params.get("search") or None,
        )
        payload = [founder_application_to_payload(app) for app in applications]
        return Response(FounderApplicationSerializer(payload, many=True).data)


class FounderApplicationDetailView(APIView):
    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsPlatformAdmin]

    @extend_schema(
        tags=["founders"],
        summary="Get City Founder application (full answers)",
        responses={200: FounderApplicationSerializer},
    )
    def get(self, request, application_id):
        application = get_founder_application_by_id(application_id)
        if application is None:
            return Response(
                {"detail": "Application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            FounderApplicationSerializer(
                founder_application_to_payload(application)
            ).data
        )

    @extend_schema(
        tags=["founders"],
        summary="Update City Founder application status",
        request=FounderApplicationStatusUpdateSerializer,
        responses={200: FounderApplicationSerializer},
    )
    def patch(self, request, application_id):
        serializer = FounderApplicationStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            application = update_founder_application_status(
                application_id=application_id,
                status=serializer.validated_data["status"],
            )
        except FounderApplicationNotFound:
            return Response(
                {"detail": "Application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            FounderApplicationSerializer(
                founder_application_to_payload(application)
            ).data
        )


class FounderApplicationSyncView(APIView):
    """Manual refresh from Google Sheets (also runs on Celery Beat 12:00 & 18:00 UTC)."""

    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsPlatformAdmin]

    @extend_schema(
        tags=["founders"],
        summary="Get last applications sync state",
        responses={200: FounderApplicationSyncStateSerializer},
    )
    def get(self, request):
        state = get_or_create_sync_state()
        return Response(
            FounderApplicationSyncStateSerializer(sync_state_to_payload(state)).data
        )

    @extend_schema(
        tags=["founders"],
        summary="Sync City Founder applications from Google Sheets",
        responses={200: FounderApplicationSyncResultSerializer},
    )
    def post(self, request):
        try:
            result = sync_founder_applications_from_sheet()
        except FounderApplicationSyncError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(FounderApplicationSyncResultSerializer(result).data)
