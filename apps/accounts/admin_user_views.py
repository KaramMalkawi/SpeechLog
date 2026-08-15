from __future__ import annotations

from django.conf import settings
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.authentication import VerifiedJWTAuthentication
from apps.accounts.models import User
from apps.accounts.permissions import IsPlatformAdmin
from apps.accounts.selectors import list_users_for_admin
from apps.accounts.serializers import (
    AdminUserCreateSerializer,
    AdminUserDeleteSerializer,
    AdminUserSerializer,
    AdminUserUpdateSerializer,
)
from apps.accounts.services import (
    AdminUserDeleteError,
    AdminUserUpdateError,
    admin_user_to_payload,
    create_user_by_admin,
    delete_user_by_admin,
    update_user_by_admin,
)
from apps.accounts.tasks import send_platform_admin_invite_email_task
from apps.founders.tasks import send_city_founder_invite_email_task
from apps.tenancy.selectors import get_city_by_id


ROLE_LABELS = {
    User.Role.ADMIN: "Admin",
    User.Role.CITY_FOUNDER: "City Founder",
    User.Role.TEAM_MEMBER: "Team Member",
    User.Role.MEMBER: "Member",
    User.Role.NON_MEMBER: "Non-Member",
}


def _send_temp_password_email(*, user: User, temporary_password: str) -> None:
    if user.role == User.Role.CITY_FOUNDER:
        from apps.founders.selectors import get_city_founder_by_user_id

        founder = get_city_founder_by_user_id(user.id)
        city = get_city_by_id(founder.city_id) if founder else None
        send_city_founder_invite_email_task.delay(
            to=user.email,
            temporary_password=temporary_password,
            recipient_name=user.full_name,
            city_name=city.name if city else "",
            country_name=city.country.name if city else "",
            login_url=settings.ADMIN_DASHBOARD_URL.rstrip("/"),
        )
        return

    send_platform_admin_invite_email_task.delay(
        to=user.email,
        temporary_password=temporary_password,
        recipient_name=user.full_name,
        login_url=(
            settings.ADMIN_DASHBOARD_URL.rstrip("/")
            if user.role == User.Role.ADMIN
            else settings.EMAIL_BRAND_WEBSITE.rstrip("/")
        ),
        role_label=ROLE_LABELS.get(user.role, user.role),
    )


class AdminUserListView(APIView):
    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsPlatformAdmin]

    @extend_schema(
        tags=["accounts"],
        summary="List all users (admin)",
        parameters=[
            OpenApiParameter(name="role", required=False, type=str),
            OpenApiParameter(name="search", required=False, type=str),
        ],
        responses={200: AdminUserSerializer(many=True)},
    )
    def get(self, request):
        users = list_users_for_admin(
            actor_id=request.user.id,
            role=request.query_params.get("role") or None,
            search=request.query_params.get("search") or None,
        )
        payload = [
            admin_user_to_payload(user, actor_id=request.user.id) for user in users
        ]
        return Response(AdminUserSerializer(payload, many=True).data)

    @extend_schema(
        tags=["accounts"],
        summary="Create a user (admin)",
        description=(
            "Creates a user with any product role (never Superadmin). "
            "City Founder requires city_id. Emails a temporary password."
        ),
        request=AdminUserCreateSerializer,
        responses={201: AdminUserSerializer},
    )
    def post(self, request):
        serializer = AdminUserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user, temporary_password = create_user_by_admin(
            actor_id=request.user.id,
            full_name=data["full_name"],
            email=data["email"],
            role=data["role"],
            city_id=data.get("city_id"),
        )

        if data["role"] == User.Role.CITY_FOUNDER:
            city = get_city_by_id(data["city_id"])
            send_city_founder_invite_email_task.delay(
                to=user.email,
                temporary_password=temporary_password,
                recipient_name=user.full_name,
                city_name=city.name if city else "",
                country_name=city.country.name if city else "",
                login_url=settings.ADMIN_DASHBOARD_URL.rstrip("/"),
            )
        else:
            send_platform_admin_invite_email_task.delay(
                to=user.email,
                temporary_password=temporary_password,
                recipient_name=user.full_name,
                login_url=(
                    settings.ADMIN_DASHBOARD_URL.rstrip("/")
                    if data["role"] == User.Role.ADMIN
                    else settings.EMAIL_BRAND_WEBSITE.rstrip("/")
                ),
                role_label=ROLE_LABELS.get(data["role"], data["role"]),
            )

        return Response(
            AdminUserSerializer(
                admin_user_to_payload(user, actor_id=request.user.id)
            ).data,
            status=status.HTTP_201_CREATED,
        )


class AdminUserDetailView(APIView):
    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsPlatformAdmin]

    @extend_schema(
        tags=["accounts"],
        summary="Update a user (admin)",
        description=(
            "Update name, email, role, active flag, residence, City Founder location/status, "
            "and optionally reset password (emails a temporary password)."
        ),
        request=AdminUserUpdateSerializer,
        responses={200: AdminUserSerializer},
    )
    def patch(self, request, user_id):
        serializer = AdminUserUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            user, temporary_password = update_user_by_admin(
                actor_id=request.user.id,
                user_id=user_id,
                **data,
            )
        except AdminUserUpdateError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if temporary_password:
            _send_temp_password_email(user=user, temporary_password=temporary_password)

        payload = admin_user_to_payload(user, actor_id=request.user.id)
        return Response(AdminUserSerializer(payload).data)

    @extend_schema(
        tags=["accounts"],
        summary="Delete a user (admin)",
        request=AdminUserDeleteSerializer,
        responses={204: None},
    )
    def delete(self, request, user_id):
        serializer = AdminUserDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            delete_user_by_admin(
                actor_id=request.user.id,
                user_id=user_id,
                confirmation_name=serializer.validated_data["confirmation_name"],
            )
        except AdminUserDeleteError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)
