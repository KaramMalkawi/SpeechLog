from __future__ import annotations

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.models import TenantScopedModel

GATHERING_HARD_CAP = 20


class Gathering(TenantScopedModel):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    # Public area (neighborhood / city area). Exact pin is separate and gated.
    area = models.CharField(max_length=255)
    exact_location = models.CharField(
        max_length=255,
        blank=True,
        help_text="Exact address / map pin — only revealed to joined attendees.",
    )
    map_link = models.URLField(max_length=500, blank=True)
    cover_image_key = models.CharField(
        max_length=512,
        blank=True,
        help_text="S3 object key for the gathering cover image.",
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    max_attendees = models.PositiveIntegerField(
        default=GATHERING_HARD_CAP,
        validators=[
            MinValueValidator(2),
            MaxValueValidator(GATHERING_HARD_CAP),
        ],
    )
    is_cancelled = models.BooleanField(default=False)
    class DeletionStatus(models.TextChoices):
        NONE = "none", "None"
        PENDING = "pending", "Pending admin approval"
        REJECTED = "rejected", "Rejected"
        APPROVED = "approved", "Approved"

    deletion_status = models.CharField(
        max_length=16,
        choices=DeletionStatus.choices,
        default=DeletionStatus.NONE,
        db_index=True,
    )
    deletion_reason = models.TextField(blank=True)
    deletion_requested_at = models.DateTimeField(null=True, blank=True)
    deletion_reviewed_at = models.DateTimeField(null=True, blank=True)
    deletion_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_gathering_deletions",
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_gatherings",
    )

    class Meta:
        ordering = ["-created_at", "title"]
        indexes = [
            models.Index(fields=["starts_at"]),
            models.Index(fields=["community_id", "starts_at"]),
            models.Index(fields=["-created_at"]),
            models.Index(fields=["deletion_status", "community_id"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(max_attendees__gte=2)
                & models.Q(max_attendees__lte=GATHERING_HARD_CAP),
                name="gathering_max_attendees_within_hard_cap",
            ),
        ]

    def __str__(self) -> str:
        return self.title


class GatheringAttendee(TenantScopedModel):
    gathering = models.ForeignKey(
        Gathering,
        on_delete=models.CASCADE,
        related_name="attendees",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="gathering_attendances",
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["gathering", "user"],
                name="uniq_gathering_attendee_per_user",
            )
        ]
        indexes = [models.Index(fields=["gathering", "is_active"])]

    def __str__(self) -> str:
        return f"{self.user_id} @ {self.gathering_id}"
