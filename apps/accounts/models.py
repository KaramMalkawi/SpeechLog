from __future__ import annotations

import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

from core.models import TenantScopedModel


class UserManager(BaseUserManager):
    def create_user(self, email: str, password: str | None = None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("verification_status", User.VerificationStatus.VERIFIED)
        extra_fields.setdefault("email_verified", True)
        extra_fields.setdefault("role", User.Role.ADMIN)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class VerificationStatus(models.TextChoices):
        UNVERIFIED = "unverified", "Unverified"
        PENDING_REVIEW = "pending_review", "Pending review"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    class Gender(models.TextChoices):
        MALE = "M", "Male"
        FEMALE = "F", "Female"

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        CITY_FOUNDER = "city_founder", "City Founder"
        TEAM_MEMBER = "team_member", "Team Member"
        MEMBER = "member", "Member"
        NON_MEMBER = "non_member", "Non-Member"

    class ResidentType(models.TextChoices):
        EXPATRIATE = "expatriate", "Expatriate"
        LOCAL = "local", "Local"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=160, blank=True)
    official_full_name = models.CharField(
        max_length=160,
        blank=True,
        help_text="Full name as read from the identity document (Didit OCR).",
    )
    phone_number = models.CharField(max_length=32, blank=True)
    location = models.CharField(
        max_length=160,
        blank=True,
        help_text="Free-text base location shown on the profile (e.g. city).",
    )
    nationality_code = models.CharField(
        max_length=2,
        blank=True,
        db_index=True,
        help_text="ISO 3166-1 alpha-2 nationality; set from ID verification OCR.",
    )
    residence_country_code = models.CharField(
        max_length=2,
        blank=True,
        db_index=True,
        help_text="ISO 3166-1 alpha-2 country of residence.",
    )
    date_of_birth = models.DateField(null=True, blank=True)
    document_expiration_date = models.DateField(null=True, blank=True)
    age = models.PositiveSmallIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=8, choices=Gender.choices, blank=True)
    role = models.CharField(
        max_length=32,
        choices=Role.choices,
        default=Role.NON_MEMBER,
        db_index=True,
        help_text="Platform role. Registration defaults to Non-Member.",
    )
    resident_type = models.CharField(
        max_length=32,
        choices=ResidentType.choices,
        blank=True,
        db_index=True,
        help_text="Expatriate when passport nationality matches residence country; Local when they differ.",
    )
    verification_status = models.CharField(
        max_length=32,
        choices=VerificationStatus.choices,
        default=VerificationStatus.UNVERIFIED,
        db_index=True,
    )
    email_verified = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True after the user confirms ownership of their email via OTP.",
    )
    registration_step = models.PositiveSmallIntegerField(default=0)
    manual_verification_approved = models.BooleanField(
        default=False,
        help_text="For Local residents: True only after an admin completes step 3 review.",
    )
    active_community_id = models.UUIDField(null=True, blank=True, db_index=True)
    bio = models.CharField(max_length=500, blank=True)
    profile_photo_key = models.CharField(
        max_length=512,
        blank=True,
        help_text="S3 object key for the user's profile photo.",
    )
    profile_onboarding_completed = models.BooleanField(
        default=False,
        db_index=True,
        help_text=(
            "True after the post-OTP profile setup screens are finished or skipped. "
            "Identity (Didit) verification is separate and optional."
        ),
    )
    gathering_attendance_credit = models.PositiveSmallIntegerField(
        default=0,
        help_text=(
            "Admin-granted attendance credits toward gathering create/join eligibility. "
            "Added on top of real scanned event tickets."
        ),
    )
    bypass_gathering_attendance = models.BooleanField(
        default=False,
        db_index=True,
        help_text=(
            "When True, admin bypasses the event-attendance gate for creating/joining "
            "gatherings (demo / support only)."
        ),
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    must_change_password = models.BooleanField(
        default=False,
        help_text="When True, City Founder must set a new password before using the dashboard.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        ordering = ["email"]
        indexes = [
            models.Index(fields=["verification_status", "is_active"]),
        ]

    def __str__(self) -> str:
        return self.email

    @property
    def is_identity_verified(self) -> bool:
        if self.verification_status != self.VerificationStatus.VERIFIED:
            return False
        if self.resident_type == self.ResidentType.LOCAL and not self.manual_verification_approved:
            return False
        return True

    @property
    def is_platform_admin(self) -> bool:
        return self.role == self.Role.ADMIN

    @property
    def is_superadmin(self) -> bool:
        """Django superuser — only actor with full Django /admin and model perms."""
        return bool(self.is_superuser)

    @property
    def is_paid_member(self) -> bool:
        """Active paid subscriber. Subscription state hooks in at Milestone 4."""
        return self.role == self.Role.MEMBER

    @property
    def is_registered_user(self) -> bool:
        return self.role in {
            self.Role.MEMBER,
            self.Role.NON_MEMBER,
            self.Role.CITY_FOUNDER,
            self.Role.TEAM_MEMBER,
            self.Role.ADMIN,
        }


class IdentityVerificationSession(models.Model):
    class Provider(models.TextChoices):
        DIDIT = "didit", "Didit"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="verification_sessions")
    provider = models.CharField(max_length=32, choices=Provider.choices, default=Provider.DIDIT)
    provider_session_id = models.UUIDField(db_index=True)
    status = models.CharField(max_length=64, default="Not Started")
    verification_url = models.URLField(max_length=500, blank=True)
    extracted_full_name = models.CharField(max_length=160, blank=True)
    extracted_nationality = models.CharField(max_length=3, blank=True)
    extracted_date_of_birth = models.DateField(null=True, blank=True)
    extracted_expiration_date = models.DateField(null=True, blank=True)
    extracted_gender = models.CharField(max_length=8, blank=True)
    last_event_id = models.UUIDField(null=True, blank=True, db_index=True)
    decision_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} @ {self.provider_session_id}"


class DiditWebhookDelivery(models.Model):
    event_id = models.UUIDField(primary_key=True)
    webhook_type = models.CharField(max_length=64, blank=True)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-received_at"]

    def __str__(self) -> str:
        return f"{self.webhook_type} @ {self.event_id}"


class CommunityMembership(TenantScopedModel):
    class Role(models.TextChoices):
        MEMBER = "member", "Member"
        TEAM_MEMBER = "team_member", "Team Member"
        CITY_FOUNDER = "city_founder", "City Founder"
        ADMIN = "admin", "Admin"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(max_length=32, choices=Role.choices, default=Role.MEMBER)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "community_id"],
                name="uniq_membership_per_user_community",
            ),
        ]
        indexes = [
            models.Index(fields=["community_id", "role"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} @ {self.community_id}"


class UserFollow(models.Model):
    follower = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="following_relations",
    )
    following = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="follower_relations",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["follower", "following"],
                name="uniq_user_follow",
            ),
            models.CheckConstraint(
                condition=~models.Q(follower=models.F("following")),
                name="prevent_self_follow",
            ),
        ]
        indexes = [
            models.Index(fields=["follower", "created_at"]),
            models.Index(fields=["following", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.follower_id} -> {self.following_id}"
