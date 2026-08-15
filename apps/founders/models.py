from __future__ import annotations

from django.conf import settings
from django.db import models

from core.models import TimeStampedModel, UUIDPrimaryKeyModel


class Founder(UUIDPrimaryKeyModel, TimeStampedModel):
    """City Founder profile — one user assigned to one operational city."""

    class Status(models.TextChoices):
        PENDING_FIRST_LOGIN = "pending_first_login", "Pending first login"
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        SUSPENDED = "suspended", "Suspended"

    OCCUPYING_STATUSES = (
        Status.PENDING_FIRST_LOGIN,
        Status.ACTIVE,
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="founder_profile",
    )
    city_id = models.UUIDField(db_index=True)
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.PENDING_FIRST_LOGIN,
        db_index=True,
    )

    class Meta:
        db_table = "city_founders"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["city_id", "status"]),
            models.Index(fields=["status", "created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["city_id"],
                condition=models.Q(status__in=["pending_first_login", "active"]),
                name="uniq_assigned_founder_per_city",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} city={self.city_id}"


class FounderApplication(UUIDPrimaryKeyModel, TimeStampedModel):
    """Cached City Founder form response (synced from Google Sheets)."""

    class Status(models.TextChoices):
        UNDER_REVIEW = "under_review", "Under review"
        REVIEWED = "reviewed", "Reviewed"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"

    sheet_row = models.PositiveIntegerField(
        unique=True,
        help_text="1-based row number in the Google Sheet (row 1 is headers).",
    )
    submitted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    email = models.EmailField(blank=True, db_index=True)
    country_name = models.CharField(max_length=255, blank=True, db_index=True)
    full_name = models.CharField(max_length=255, blank=True)
    answers = models.JSONField(
        default=dict,
        blank=True,
        help_text="Full form row keyed by original sheet headers.",
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.UNDER_REVIEW,
        db_index=True,
    )
    spreadsheet_id = models.CharField(max_length=128, blank=True)
    sheet_gid = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ["-submitted_at", "-sheet_row"]
        indexes = [
            models.Index(fields=["status", "submitted_at"]),
            models.Index(fields=["country_name", "submitted_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.email or self.sheet_row} ({self.status})"


class FounderApplicationSyncState(models.Model):
    """Singleton row tracking the last Google Sheets sync."""

    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_sync_error = models.TextField(blank=True)
    last_sync_row_count = models.PositiveIntegerField(default=0)
    spreadsheet_id = models.CharField(max_length=128, blank=True)
    spreadsheet_url = models.URLField(blank=True, max_length=512)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Founder application sync state"
        verbose_name_plural = "Founder application sync state"

    def __str__(self) -> str:
        return f"sync@{self.last_synced_at or 'never'}"
