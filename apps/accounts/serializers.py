from __future__ import annotations

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.accounts.services import authenticate_admin_user, authenticate_verified_user


class RegisterSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=80)
    last_name = serializers.CharField(max_length=80)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)

    def validate_first_name(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("First name is required.")
        return cleaned

    def validate_last_name(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Last name is required.")
        return cleaned

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value

    def validate_email(self, value: str) -> str:
        normalized = User.objects.normalize_email(value)
        if User.objects.filter(email=normalized).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return normalized

    def validate(self, attrs):
        attrs["full_name"] = f"{attrs['first_name']} {attrs['last_name']}".strip()
        return attrs


class VerificationStartSerializer(serializers.Serializer):
    callback_url = serializers.URLField(required=False)


class StartVerificationResponseSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    verification_url = serializers.URLField()
    status = serializers.CharField()


class RegisterResponseSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    email = serializers.EmailField()
    full_name = serializers.CharField()
    verification_status = serializers.CharField()
    email_verified = serializers.BooleanField()
    registration_step = serializers.IntegerField()
    registration_token = serializers.CharField()
    next_step = serializers.CharField()
    message = serializers.CharField()


class EmailOTPVerifySerializer(serializers.Serializer):
    otp = serializers.CharField(min_length=6, max_length=6, trim_whitespace=True)

    def validate_otp(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned.isdigit():
            raise serializers.ValidationError("Enter the 6-digit code from your email.")
        return cleaned


class EmailOTPVerifyResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    email_verified = serializers.BooleanField()
    user_id = serializers.UUIDField()
    next_step = serializers.CharField()
    email = serializers.EmailField(required=False)
    full_name = serializers.CharField(required=False, allow_blank=True)
    access = serializers.CharField(required=False)
    refresh = serializers.CharField(required=False)


class EmailOTPResendResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    email_verified = serializers.BooleanField()


class RegistrationStatusSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    email = serializers.EmailField()
    full_name = serializers.CharField()
    official_full_name = serializers.CharField(required=False, allow_blank=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    document_expiration_date = serializers.DateField(required=False, allow_null=True)
    age = serializers.IntegerField(required=False, allow_null=True)
    gender = serializers.CharField(required=False, allow_blank=True)
    role = serializers.CharField()
    resident_type = serializers.CharField(required=False, allow_blank=True)
    manual_verification_approved = serializers.BooleanField(required=False)
    verification_status = serializers.CharField()
    email_verified = serializers.BooleanField()
    registration_step = serializers.IntegerField()
    identity_verification_required = serializers.BooleanField()
    next_step = serializers.CharField()
    didit_status = serializers.CharField(required=False, allow_blank=True)
    extracted_nationality = serializers.CharField(required=False, allow_blank=True)


class LoginIncompleteResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    code = serializers.CharField()
    next_step = serializers.CharField()
    email = serializers.EmailField()
    full_name = serializers.CharField(allow_blank=True)
    registration_token = serializers.CharField()
    email_verified = serializers.BooleanField()
    verification_status = serializers.CharField()


class LoginSuccessResponseSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    access = serializers.CharField()
    user_id = serializers.UUIDField()
    role = serializers.CharField()
    verification_status = serializers.CharField()
    email = serializers.EmailField()
    full_name = serializers.CharField(allow_blank=True)
    next_step = serializers.CharField()


class LoginSerializer(TokenObtainPairSerializer):
    username_field = User.USERNAME_FIELD

    def validate(self, attrs):
        from apps.accounts.onboarding import resolve_onboarding_step
        from apps.accounts.services import (
            EmailVerificationRequired,
            IdentityVerificationRequired,
            ManualVerificationRequired,
            RegistrationIncomplete,
            issue_registration_token,
        )

        try:
            user = authenticate_verified_user(
                email=attrs[self.username_field],
                password=attrs["password"],
            )
        except (
            EmailVerificationRequired,
            IdentityVerificationRequired,
            ManualVerificationRequired,
        ) as exc:
            user = getattr(exc, "user", None)
            if user is None:
                raise
            code = exc.default_code
            raise RegistrationIncomplete(
                payload={
                    "detail": str(exc.default_detail),
                    "code": code,
                    "next_step": resolve_onboarding_step(user),
                    "email": user.email,
                    "full_name": user.full_name,
                    "registration_token": issue_registration_token(user),
                    "email_verified": user.email_verified,
                    "verification_status": user.verification_status,
                }
            ) from exc

        from apps.founders.services import mark_founder_active_after_first_login

        mark_founder_active_after_first_login(user_id=user.id)
        refresh = RefreshToken.for_user(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user_id": str(user.id),
            "role": user.role,
            "verification_status": user.verification_status,
            "email": user.email,
            "full_name": user.full_name,
            "next_step": resolve_onboarding_step(user),
        }


class AdminLoginSerializer(TokenObtainPairSerializer):
    """Issues JWTs for Admin-role users or Django superusers."""

    username_field = User.USERNAME_FIELD

    def validate(self, attrs):
        user = authenticate_admin_user(
            email=attrs[self.username_field],
            password=attrs["password"],
        )
        refresh = RefreshToken.for_user(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user_id": str(user.id),
            "role": user.role,
            "is_superuser": user.is_superuser,
            "verification_status": user.verification_status,
            "email": user.email,
            "full_name": user.full_name,
        }


class DashboardLoginSerializer(TokenObtainPairSerializer):
    """Issues JWTs for Admin or City Founder web-dashboard actors."""

    username_field = User.USERNAME_FIELD

    def validate(self, attrs):
        from apps.accounts.services import authenticate_dashboard_user
        from apps.founders.services import mark_founder_active_after_first_login

        user = authenticate_dashboard_user(
            email=attrs[self.username_field],
            password=attrs["password"],
        )
        # First successful dashboard login promotes pending → active.
        mark_founder_active_after_first_login(user_id=user.id)
        refresh = RefreshToken.for_user(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user_id": str(user.id),
            "role": user.role,
            "is_superuser": user.is_superuser,
            "verification_status": user.verification_status,
            "email": user.email,
            "full_name": user.full_name,
            "must_change_password": user.must_change_password,
        }


class AdminLoginResponseSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    access = serializers.CharField()
    user_id = serializers.UUIDField()
    role = serializers.CharField()
    is_superuser = serializers.BooleanField()
    verification_status = serializers.CharField()
    email = serializers.EmailField()
    full_name = serializers.CharField(allow_blank=True)
    must_change_password = serializers.BooleanField(required=False, default=False)


class TokenRefreshResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetRequestResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)

    def validate_new_password(self, value: str) -> str:
        validate_password(value)
        return value


class PasswordResetConfirmResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


class AdminUserSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    full_name = serializers.CharField(allow_blank=True)
    email = serializers.EmailField()
    role = serializers.CharField()
    is_superuser = serializers.BooleanField()
    is_active = serializers.BooleanField()
    must_change_password = serializers.BooleanField()
    phone_number = serializers.CharField(allow_blank=True)
    created_at = serializers.DateTimeField()
    residence_country_code = serializers.CharField(allow_blank=True)
    residence_country_name = serializers.CharField(allow_blank=True)
    is_current_user = serializers.BooleanField()
    can_delete = serializers.BooleanField()
    can_edit = serializers.BooleanField()
    can_edit_role = serializers.BooleanField()
    founder_id = serializers.UUIDField(allow_null=True)
    city_id = serializers.UUIDField(allow_null=True)
    city_name = serializers.CharField(allow_blank=True)
    country_id = serializers.UUIDField(allow_null=True)
    country_name = serializers.CharField(allow_blank=True)
    country_code = serializers.CharField(allow_blank=True)
    founder_status = serializers.CharField(allow_blank=True)
    gathering_attendance_credit = serializers.IntegerField()
    bypass_gathering_attendance = serializers.BooleanField()
    events_scanned = serializers.IntegerField()


class AdminUserDeleteSerializer(serializers.Serializer):
    confirmation_name = serializers.CharField(max_length=160)


class AdminUserUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=160, required=False)
    email = serializers.EmailField(required=False)
    role = serializers.ChoiceField(choices=User.Role.choices, required=False)
    is_active = serializers.BooleanField(required=False)
    phone_number = serializers.CharField(max_length=32, required=False, allow_blank=True)
    residence_country_code = serializers.CharField(
        max_length=2, required=False, allow_blank=True
    )
    city_id = serializers.UUIDField(required=False, allow_null=True)
    founder_status = serializers.ChoiceField(
        choices=[
            ("pending_first_login", "Pending first login"),
            ("active", "Active"),
            ("inactive", "Inactive"),
            ("suspended", "Suspended"),
        ],
        required=False,
    )
    reset_password = serializers.BooleanField(required=False, default=False)
    gathering_attendance_credit = serializers.IntegerField(
        required=False, min_value=0, max_value=99
    )
    bypass_gathering_attendance = serializers.BooleanField(required=False)

    def validate(self, attrs):
        role = attrs.get("role")
        if role == User.Role.CITY_FOUNDER and "city_id" in attrs and attrs.get("city_id") is None:
            raise serializers.ValidationError(
                {"city_id": "Select a city when assigning the City Founder role."}
            )
        return attrs


class AdminUserCreateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=160)
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=User.Role.choices)
    city_id = serializers.UUIDField(required=False, allow_null=True)

    def validate(self, attrs):
        if attrs["role"] == User.Role.CITY_FOUNDER and not attrs.get("city_id"):
            raise serializers.ValidationError(
                {"city_id": "Select a city when creating a City Founder."}
            )
        return attrs


class PlatformAdminSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    full_name = serializers.CharField(allow_blank=True)
    email = serializers.EmailField()
    status = serializers.CharField()
    is_superuser = serializers.BooleanField()
    is_active = serializers.BooleanField()
    must_change_password = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    is_current_user = serializers.BooleanField()
    can_delete = serializers.BooleanField()
    can_edit = serializers.BooleanField()


class PlatformAdminCreateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=160)
    email = serializers.EmailField()


class PlatformAdminUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=160, required=False)
    email = serializers.EmailField(required=False)
    status = serializers.ChoiceField(
        choices=[
            ("pending_first_login", "Pending first login"),
            ("active", "Active"),
            ("suspended", "Suspended"),
        ],
        required=False,
    )


class PlatformAdminDeleteSerializer(serializers.Serializer):
    confirmation_name = serializers.CharField(max_length=160)


class DashboardChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)

    def validate_new_password(self, value: str) -> str:
        validate_password(value)
        return value


class DashboardProfileUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=160)

    def validate_full_name(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Full name is required.")
        return cleaned


class DashboardProfileSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    email = serializers.EmailField()
    full_name = serializers.CharField()
