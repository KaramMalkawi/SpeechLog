from __future__ import annotations

from uuid import UUID

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.authentication import VerifiedJWTAuthentication
from apps.accounts.didit.client import DiditError
from apps.accounts.didit.services import (
    refresh_user_verification_from_didit,
    start_didit_verification_session,
)
from apps.accounts.onboarding import resolve_onboarding_step
from apps.accounts.permissions import IsIdentityVerified
from apps.accounts.profile_selectors import get_own_profile, get_profile_photo_url, get_public_profile
from apps.accounts.profile_serializers import (
    IdentityVerificationStartResponseSerializer,
    IdentityVerificationStatusSerializer,
    MemberChangePasswordResponseSerializer,
    MemberChangePasswordSerializer,
    ProfileOnboardingCompleteResponseSerializer,
    ProfileOnboardingCompleteSerializer,
    ProfilePhotoConfirmResponseSerializer,
    ProfilePhotoConfirmSerializer,
    ProfilePhotoPresignResponseSerializer,
    ProfilePhotoPresignSerializer,
    ProfileSerializer,
    ProfileUpdateSerializer,
)
from apps.accounts.profile_services import (
    ProfilePhotoError,
    ProfileUpdateError,
    activate_annual_membership,
    build_profile_payload,
    complete_profile_onboarding,
    confirm_profile_photo_upload,
    create_profile_photo_upload,
    remove_profile_photo,
    update_profile_details,
)
from apps.accounts.services import change_own_password


class MyProfileView(APIView):
    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsAuthenticated, IsIdentityVerified]

    @extend_schema(
        tags=["accounts"],
        summary="Get my profile",
        responses={200: ProfileSerializer},
    )
    def get(self, request):
        from apps.accounts.services import ensure_user_has_active_community

        user = ensure_user_has_active_community(user=request.user)
        profile = get_own_profile(user)
        return Response(build_profile_payload(user=profile, viewer=user))

    @extend_schema(
        tags=["accounts"],
        summary="Update my profile",
        request=ProfileUpdateSerializer,
        responses={200: ProfileSerializer},
    )
    def patch(self, request):
        serializer = ProfileUpdateSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        try:
            user = update_profile_details(user=request.user, **serializer.validated_data)
        except ProfileUpdateError as exc:
            return Response(
                {"full_name": [str(exc)]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        profile = get_own_profile(user)
        return Response(build_profile_payload(user=profile, viewer=request.user))


class MemberChangePasswordView(APIView):
    """Mobile app password change from Personal Information."""

    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsAuthenticated, IsIdentityVerified]

    @extend_schema(
        tags=["accounts"],
        summary="Change own password",
        request=MemberChangePasswordSerializer,
        responses={200: MemberChangePasswordResponseSerializer},
    )
    def post(self, request):
        serializer = MemberChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            change_own_password(
                user_id=request.user.id,
                current_password=serializer.validated_data["current_password"],
                new_password=serializer.validated_data["new_password"],
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "Password updated successfully."})


class IdentityVerificationStartView(APIView):
    """Start Didit identity verification for a signed-in mobile user."""

    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsAuthenticated, IsIdentityVerified]

    @extend_schema(
        tags=["accounts"],
        summary="Start identity verification (Didit)",
        request={
            "application/json": {
                "type": "object",
                "properties": {"callback_url": {"type": "string", "format": "uri"}},
            }
        },
        responses={201: IdentityVerificationStartResponseSerializer, 200: IdentityVerificationStartResponseSerializer},
    )
    def post(self, request):
        user = request.user
        if user.is_identity_verified:
            return Response(
                {
                    "detail": "Identity is already verified.",
                    "is_identity_verified": True,
                    "status": user.verification_status,
                    "verification_status": user.verification_status,
                    "session_id": None,
                    "verification_url": "",
                }
            )

        if user.verification_status == user.VerificationStatus.PENDING_REVIEW:
            return Response(
                {
                    "detail": "Identity verification is pending admin review.",
                    "is_identity_verified": False,
                    "status": user.verification_status,
                    "verification_status": user.verification_status,
                    "session_id": None,
                    "verification_url": "",
                }
            )

        callback_url = ""
        if isinstance(request.data, dict):
            callback_url = str(request.data.get("callback_url") or "").strip()
        callback_url = callback_url or settings.DIDIT_CALLBACK_URL
        if not callback_url:
            return Response(
                {"detail": "callback_url is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            session = start_didit_verification_session(
                user=user,
                callback_url=callback_url,
            )
        except DiditError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(
            {
                "session_id": session.provider_session_id,
                "verification_url": session.verification_url,
                "status": session.status,
                "verification_status": user.verification_status,
                "is_identity_verified": False,
            },
            status=status.HTTP_201_CREATED,
        )


class IdentityVerificationStatusView(APIView):
    """Refresh Didit decision and return current identity verification state."""

    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsAuthenticated, IsIdentityVerified]

    @extend_schema(
        tags=["accounts"],
        summary="Get identity verification status",
        responses={200: IdentityVerificationStatusSerializer},
    )
    def get(self, request):
        from apps.tenancy.country_data import get_country_by_code

        session = refresh_user_verification_from_didit(request.user)
        request.user.refresh_from_db()
        user = request.user
        nationality = (
            get_country_by_code(user.nationality_code) if user.nationality_code else None
        )
        return Response(
            {
                "is_identity_verified": user.is_identity_verified,
                "verification_status": user.verification_status,
                "didit_status": session.status if session is not None else None,
                "full_name": user.full_name or "",
                "official_full_name": user.official_full_name or "",
                "nationality_code": user.nationality_code or "",
                "nationality_name": nationality.name if nationality else "",
            }
        )


class MembershipActivateView(APIView):
    """Demo membership checkout completion until real payment gateway lands."""

    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsAuthenticated, IsIdentityVerified]

    @extend_schema(
        tags=["accounts"],
        summary="Activate membership (demo checkout)",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "plan": {
                        "type": "string",
                        "enum": ["monthly", "annual"],
                    }
                },
            }
        },
        responses={200: dict},
    )
    def post(self, request):
        plan = request.data.get("plan", "annual") if isinstance(request.data, dict) else "annual"
        result = activate_annual_membership(user=request.user, plan=plan)
        return Response(result)


class ProfileOnboardingCompleteView(APIView):
    """Finish or skip the post-OTP profile setup screens."""

    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsAuthenticated, IsIdentityVerified]

    @extend_schema(
        tags=["accounts"],
        summary="Complete or skip profile onboarding",
        request=ProfileOnboardingCompleteSerializer,
        responses={200: ProfileOnboardingCompleteResponseSerializer},
    )
    def post(self, request):
        serializer = ProfileOnboardingCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        detail_fields = {
            key: data[key]
            for key in ("bio", "location", "phone_number")
            if key in data
        }
        user = request.user
        if detail_fields:
            user = update_profile_details(user=user, **detail_fields)
        user = complete_profile_onboarding(user=user)

        return Response(
            {
                "detail": (
                    "Profile setup skipped."
                    if data.get("skipped")
                    else "Profile setup completed."
                ),
                "next_step": resolve_onboarding_step(user),
                "profile_onboarding_completed": user.profile_onboarding_completed,
            }
        )


class ProfilePhotoPresignView(APIView):
    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsAuthenticated, IsIdentityVerified]

    @extend_schema(
        tags=["accounts"],
        summary="Get presigned S3 upload URL for profile photo",
        request=ProfilePhotoPresignSerializer,
        responses={201: ProfilePhotoPresignResponseSerializer},
    )
    def post(self, request):
        serializer = ProfilePhotoPresignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            presigned = create_profile_photo_upload(
                user=request.user,
                content_type=serializer.validated_data["content_type"],
                content_length=serializer.validated_data["content_length"],
            )
        except ProfilePhotoError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(presigned, status=status.HTTP_201_CREATED)


class ProfilePhotoConfirmView(APIView):
    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsAuthenticated, IsIdentityVerified]

    @extend_schema(
        tags=["accounts"],
        summary="Confirm profile photo upload",
        request=ProfilePhotoConfirmSerializer,
        responses={200: ProfilePhotoConfirmResponseSerializer},
    )
    def post(self, request):
        serializer = ProfilePhotoConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = confirm_profile_photo_upload(
                user=request.user,
                object_key=serializer.validated_data["object_key"],
            )
        except ProfilePhotoError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"photo_url": get_profile_photo_url(user)})


class ProfilePhotoDeleteView(APIView):
    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsAuthenticated, IsIdentityVerified]

    @extend_schema(
        tags=["accounts"],
        summary="Remove profile photo",
        responses={204: None},
    )
    def delete(self, request):
        try:
            remove_profile_photo(user=request.user)
        except ProfilePhotoError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserProfileView(APIView):
    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsAuthenticated, IsIdentityVerified]

    @extend_schema(
        tags=["accounts"],
        summary="Get a user's public profile",
        responses={200: ProfileSerializer},
    )
    def get(self, request, user_id: UUID):
        profile = get_public_profile(user_id=user_id, viewer=request.user)
        if profile is None:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(build_profile_payload(user=profile, viewer=request.user))
