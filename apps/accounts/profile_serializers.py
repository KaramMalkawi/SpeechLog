from __future__ import annotations

from rest_framework import serializers


class ProfileSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    full_name = serializers.CharField()
    bio = serializers.CharField()
    location = serializers.CharField(required=False, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    photo_url = serializers.URLField(allow_blank=True)
    role = serializers.CharField()
    followers_count = serializers.IntegerField()
    following_count = serializers.IntegerField()
    membership_status = serializers.CharField()
    active_community_id = serializers.UUIDField(allow_null=True)
    is_following = serializers.BooleanField()
    is_own_profile = serializers.BooleanField()
    profile_onboarding_completed = serializers.BooleanField(required=False)
    next_step = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    is_identity_verified = serializers.BooleanField(required=False)
    verification_status = serializers.CharField(required=False)
    official_full_name = serializers.CharField(required=False, allow_blank=True)
    display_name_locked = serializers.BooleanField(required=False)
    nationality_code = serializers.CharField(required=False, allow_blank=True)
    nationality_name = serializers.CharField(required=False, allow_blank=True)
    membership_id = serializers.CharField(required=False, allow_blank=True)
    membership_display_name = serializers.CharField(required=False, allow_blank=True)


class MemberChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)

    def validate_new_password(self, value: str) -> str:
        from django.contrib.auth.password_validation import validate_password

        validate_password(value)
        return value


class MemberChangePasswordResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


class IdentityVerificationStartResponseSerializer(serializers.Serializer):
    session_id = serializers.UUIDField(required=False, allow_null=True)
    verification_url = serializers.URLField(required=False, allow_blank=True)
    status = serializers.CharField()
    is_identity_verified = serializers.BooleanField()
    detail = serializers.CharField(required=False)


class IdentityVerificationStatusSerializer(serializers.Serializer):
    is_identity_verified = serializers.BooleanField()
    verification_status = serializers.CharField()
    didit_status = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    full_name = serializers.CharField(required=False, allow_blank=True)
    official_full_name = serializers.CharField(required=False, allow_blank=True)
    nationality_code = serializers.CharField(required=False, allow_blank=True)
    nationality_name = serializers.CharField(required=False, allow_blank=True)


class ProfileUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=160, allow_blank=False, required=False)
    bio = serializers.CharField(max_length=500, allow_blank=True, required=False)
    location = serializers.CharField(max_length=160, allow_blank=True, required=False)
    phone_number = serializers.CharField(max_length=32, allow_blank=True, required=False)

    def validate_full_name(self, value):
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Full name cannot be blank.")
        request = self.context.get("request")
        user = getattr(request, "user", None) if request is not None else None
        if user is not None and (getattr(user, "official_full_name", None) or "").strip():
            raise serializers.ValidationError(
                "Display name is locked after identity verification."
            )
        return name

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Provide at least one field to update.")
        return attrs


class ProfileOnboardingCompleteSerializer(serializers.Serializer):
    """Finish or skip post-OTP profile setup. Optional fields are saved when present."""

    bio = serializers.CharField(max_length=500, allow_blank=True, required=False)
    location = serializers.CharField(max_length=160, allow_blank=True, required=False)
    phone_number = serializers.CharField(max_length=32, allow_blank=True, required=False)
    skipped = serializers.BooleanField(required=False, default=False)


class ProfileOnboardingCompleteResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    next_step = serializers.CharField()
    profile_onboarding_completed = serializers.BooleanField()


class ProfilePhotoPresignSerializer(serializers.Serializer):
    content_type = serializers.CharField(max_length=100)
    content_length = serializers.IntegerField(min_value=1)


class ProfilePhotoPresignResponseSerializer(serializers.Serializer):
    upload_url = serializers.URLField()
    object_key = serializers.CharField()
    expires_in = serializers.IntegerField()
    headers = serializers.DictField(child=serializers.CharField())


class ProfilePhotoConfirmSerializer(serializers.Serializer):
    object_key = serializers.CharField(max_length=512)


class ProfilePhotoConfirmResponseSerializer(serializers.Serializer):
    photo_url = serializers.URLField()
