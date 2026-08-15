from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import HttpResponseNotFound
from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts.authentication import RegistrationJWTAuthentication, VerifiedJWTAuthentication
from apps.accounts.didit.client import DiditError
from apps.accounts.didit.services import (
    refresh_user_verification_from_didit,
    start_didit_verification_session,
)
from apps.accounts.permissions import IsIdentityVerified, IsPlatformAdmin
from apps.accounts.serializers import (
    AdminLoginResponseSerializer,
    AdminLoginSerializer,
    DashboardChangePasswordSerializer,
    DashboardLoginSerializer,
    DashboardProfileSerializer,
    DashboardProfileUpdateSerializer,
    EmailOTPResendResponseSerializer,
    EmailOTPVerifyResponseSerializer,
    EmailOTPVerifySerializer,
    LoginIncompleteResponseSerializer,
    LoginSerializer,
    LoginSuccessResponseSerializer,
    PasswordResetConfirmResponseSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestResponseSerializer,
    PasswordResetRequestSerializer,
    RegisterResponseSerializer,
    RegisterSerializer,
    RegistrationStatusSerializer,
    StartVerificationResponseSerializer,
    TokenRefreshResponseSerializer,
    VerificationStartSerializer,
)
from apps.accounts.services import (
    PASSWORD_RESET_REQUEST_MESSAGE,
    PASSWORD_RESET_SUCCESS_MESSAGE,
    EMAIL_OTP_SENT_MESSAGE,
    EMAIL_OTP_VERIFIED_MESSAGE,
    EmailAlreadyVerified,
    EmailOTPInvalid,
    EmailOTPRateLimited,
    InvalidPasswordResetToken,
    RegistrationIncomplete,
    change_dashboard_password,
    update_dashboard_profile,
    PasswordResetRateLimited,
    confirm_password_reset,
    issue_registration_token,
    register_user,
    request_email_verification_otp,
    request_password_reset,
    verify_email_otp,
)
from apps.adminpanel.services import ADMIN_LOGIN_ACTION, record_admin_audit_event


def _client_ip(request) -> str:
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def _user_profile_payload(user) -> dict:
    from apps.accounts.onboarding import resolve_onboarding_step

    return {
        "user_id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "official_full_name": user.official_full_name,
        "date_of_birth": user.date_of_birth,
        "document_expiration_date": user.document_expiration_date,
        "age": user.age,
        "gender": user.gender,
        "role": user.role,
        "resident_type": user.resident_type,
        "manual_verification_approved": user.manual_verification_approved,
        "verification_status": user.verification_status,
        "email_verified": user.email_verified,
        "registration_step": user.registration_step,
        "identity_verification_required": not user.is_identity_verified,
        "next_step": resolve_onboarding_step(user),
    }


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["accounts"],
        summary="Create account",
        description=(
            "Creates an unverified account from first name, last name, email, and "
            "password, then emails a one-time verification code. Nationality, "
            "residence country, and phone are collected in later steps. Returns a "
            "registration token for continuing onboarding. Sign-in is blocked until "
            "identity verification completes."
        ),
        request=RegisterSerializer,
        responses={201: RegisterResponseSerializer},
        auth=[],
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            user = register_user(
                full_name=data["full_name"],
                email=data["email"],
                password=data["password"],
                request_ip=_client_ip(request),
            )
        except EmailOTPRateLimited:
            return Response(
                {"detail": "Too many verification emails. Try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "user_id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "verification_status": user.verification_status,
                "email_verified": user.email_verified,
                "registration_step": user.registration_step,
                "registration_token": issue_registration_token(user),
                "next_step": "verify_email",
                "message": (
                    "Account created. Enter the verification code sent to your email."
                ),
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyEmailOTPView(APIView):
    authentication_classes = [RegistrationJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["accounts"],
        summary="Verify email OTP",
        description="Confirms email ownership with the one-time code sent after registration.",
        request=EmailOTPVerifySerializer,
        responses={200: EmailOTPVerifyResponseSerializer},
    )
    def post(self, request):
        from rest_framework_simplejwt.tokens import RefreshToken

        from apps.accounts.onboarding import resolve_onboarding_step

        serializer = EmailOTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = verify_email_otp(user=request.user, otp=serializer.validated_data["otp"])
            detail = EMAIL_OTP_VERIFIED_MESSAGE
        except EmailAlreadyVerified:
            user = request.user
            detail = "Email is already verified."
        except EmailOTPInvalid as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        # Issue access tokens once email is verified so the client can run
        # authenticated profile onboarding (photo + details) and then home.
        # Identity (Didit) verification remains optional.
        next_step = resolve_onboarding_step(user)
        payload = {
            "detail": detail,
            "email_verified": user.email_verified,
            "user_id": user.id,
            "next_step": next_step,
            "full_name": user.full_name,
            "email": user.email,
        }
        if user.email_verified:
            refresh = RefreshToken.for_user(user)
            payload["access"] = str(refresh.access_token)
            payload["refresh"] = str(refresh)
        return Response(payload, status=status.HTTP_200_OK)


class ResendEmailOTPView(APIView):
    authentication_classes = [RegistrationJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["accounts"],
        summary="Resend email OTP",
        description="Issues a new email verification code. Rate-limited per email and IP.",
        request=None,
        responses={200: EmailOTPResendResponseSerializer},
    )
    def post(self, request):
        try:
            request_email_verification_otp(
                user=request.user,
                request_ip=_client_ip(request),
            )
        except EmailAlreadyVerified:
            return Response(
                {
                    "detail": "Email is already verified.",
                    "email_verified": True,
                },
                status=status.HTTP_200_OK,
            )
        except EmailOTPRateLimited:
            return Response(
                {"detail": "Too many verification emails. Try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        return Response(
            {
                "detail": EMAIL_OTP_SENT_MESSAGE,
                "email_verified": False,
            },
            status=status.HTTP_200_OK,
        )


class RegistrationStatusView(APIView):
    authentication_classes = [RegistrationJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["accounts"],
        summary="Registration status",
        description="Returns registration progress for the current registration token.",
        responses={200: RegistrationStatusSerializer},
    )
    def get(self, request):
        user = request.user
        session = refresh_user_verification_from_didit(user)
        user.refresh_from_db()
        payload = _user_profile_payload(user)
        if session is not None:
            payload["didit_status"] = session.status
            payload["extracted_nationality"] = session.extracted_nationality
        return Response(payload)


class StartVerificationView(APIView):
    authentication_classes = [RegistrationJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["accounts"],
        summary="Start identity verification (Didit)",
        description="Creates a Didit OCR session and returns the hosted verification URL.",
        request=VerificationStartSerializer,
        responses={201: StartVerificationResponseSerializer},
    )
    def post(self, request):
        if not request.user.email_verified:
            return Response(
                {
                    "detail": "Verify your email before starting identity verification.",
                    "code": "email_verification_required",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        callback_url = request.data.get("callback_url") or settings.DIDIT_CALLBACK_URL
        if not callback_url:
            return Response(
                {"detail": "callback_url is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            session = start_didit_verification_session(
                user=request.user,
                callback_url=callback_url,
            )
        except DiditError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(
            {
                "session_id": session.provider_session_id,
                "verification_url": session.verification_url,
                "status": session.status,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["accounts"],
        summary="Sign in",
        description=(
            "Issues JWT tokens for fully verified users. Incomplete registration "
            "returns 403 with next_step and a registration_token to resume onboarding."
        ),
        request=LoginSerializer,
        responses={
            200: LoginSuccessResponseSerializer,
            403: LoginIncompleteResponseSerializer,
        },
        auth=[],
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except RegistrationIncomplete as exc:
            return Response(exc.payload, status=status.HTTP_403_FORBIDDEN)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class AdminLoginView(TokenObtainPairView):
    serializer_class = AdminLoginSerializer
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["accounts"],
        summary="Admin sign in",
        description=(
            "Issues JWT tokens for Admin-role users or Django superusers. "
            "All other roles are rejected."
        ),
        auth=[],
        request=AdminLoginSerializer,
        responses={200: AdminLoginResponseSerializer},
    )
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            record_admin_audit_event(
                actor_id=response.data["user_id"],
                action=ADMIN_LOGIN_ACTION,
                metadata={
                    "ip": _client_ip(request),
                    "user_agent": request.META.get("HTTP_USER_AGENT", ""),
                },
            )
        return response


class DashboardLoginView(TokenObtainPairView):
    """Shared web-dashboard login for Admin and City Founder."""

    serializer_class = DashboardLoginSerializer
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["accounts"],
        summary="Dashboard sign in",
        description=(
            "Issues JWT tokens for Admin or City Founder accounts (and Django "
            "superusers). Members and Non-Members are rejected."
        ),
        auth=[],
        request=DashboardLoginSerializer,
        responses={200: AdminLoginResponseSerializer},
    )
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code != status.HTTP_200_OK:
            return response

        role = response.data.get("role")
        is_superuser = response.data.get("is_superuser")
        if role == "admin" or is_superuser:
            record_admin_audit_event(
                actor_id=response.data["user_id"],
                action=ADMIN_LOGIN_ACTION,
                metadata={
                    "ip": _client_ip(request),
                    "user_agent": request.META.get("HTTP_USER_AGENT", ""),
                },
            )
        return response


class RefreshTokenView(TokenRefreshView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["accounts"],
        summary="Refresh access token",
        responses={200: TokenRefreshResponseSerializer},
    )
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code != status.HTTP_200_OK:
            return response

        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken(request.data["refresh"])
        user_id = refresh.get("user_id")
        if user_id:
            from apps.accounts.models import User

            try:
                user = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                return Response(
                    {"detail": "User not found."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            if (
                not user.email_verified
                and not user.is_staff
                and not user.is_platform_admin
                and not user.is_superadmin
            ):
                return Response(
                    {
                        "detail": "Verify your email before you can sign in.",
                        "code": "email_verification_required",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
        return response


class PasswordResetRequestView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["accounts"],
        summary="Request password reset",
        description=(
            "Sends a password reset email if an active account exists. "
            "Always returns the same response to prevent email enumeration."
        ),
        request=PasswordResetRequestSerializer,
        responses={200: PasswordResetRequestResponseSerializer},
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            request_password_reset(
                email=serializer.validated_data["email"],
                request_ip=_client_ip(request),
            )
        except PasswordResetRateLimited:
            return Response(
                {
                    "detail": "Too many password reset attempts. Please try again later.",
                    "code": "password_reset_rate_limited",
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        return Response({"detail": PASSWORD_RESET_REQUEST_MESSAGE})


class PasswordResetConfirmView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["accounts"],
        summary="Confirm password reset",
        description="Sets a new password using the single-use token from the reset email.",
        request=PasswordResetConfirmSerializer,
        responses={200: PasswordResetConfirmResponseSerializer},
    )
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            confirm_password_reset(
                token=serializer.validated_data["token"],
                new_password=serializer.validated_data["new_password"],
            )
        except InvalidPasswordResetToken:
            return Response(
                {
                    "detail": "This password reset link is invalid or has expired.",
                    "code": "invalid_password_reset_token",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except DjangoValidationError as exc:
            return Response(
                {"new_password": exc.messages},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"detail": PASSWORD_RESET_SUCCESS_MESSAGE})


class MeView(APIView):
    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsAuthenticated, IsIdentityVerified]

    @extend_schema(
        tags=["accounts"],
        summary="Current user",
        responses={200: RegistrationStatusSerializer},
    )
    def get(self, request):
        return Response(_user_profile_payload(request.user))


class DashboardChangePasswordView(APIView):
    """Platform Admin password change (Settings → Security)."""

    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsPlatformAdmin]

    @extend_schema(
        tags=["accounts"],
        summary="Change dashboard password",
        request=DashboardChangePasswordSerializer,
        responses={200: PasswordResetConfirmResponseSerializer},
    )
    def post(self, request):
        serializer = DashboardChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            change_dashboard_password(
                user_id=request.user.id,
                current_password=serializer.validated_data["current_password"],
                new_password=serializer.validated_data["new_password"],
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "Password updated successfully."})


class DashboardProfileUpdateView(APIView):
    """Platform Admin updates display name (Settings → Account)."""

    authentication_classes = [VerifiedJWTAuthentication]
    permission_classes = [IsPlatformAdmin]

    @extend_schema(
        tags=["accounts"],
        summary="Update dashboard profile",
        request=DashboardProfileUpdateSerializer,
        responses={200: DashboardProfileSerializer},
    )
    def patch(self, request):
        serializer = DashboardProfileUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = update_dashboard_profile(
                user_id=request.user.id,
                full_name=serializer.validated_data["full_name"],
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            DashboardProfileSerializer(
                {
                    "user_id": user.id,
                    "email": user.email,
                    "full_name": user.full_name,
                }
            ).data
        )


class VerifyTestPageView(TemplateView):
    template_name = "verify_test.html"

    def dispatch(self, request, *args, **kwargs):
        if not settings.VERIFY_TEST_PAGE_ENABLED:
            return HttpResponseNotFound("Not found.")
        return super().dispatch(request, *args, **kwargs)
