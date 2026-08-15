from __future__ import annotations

from django.conf import settings
from django.db import models

from core.models import TenantScopedModel


class EventCategory(models.TextChoices):
    SOCIAL = "social", "Social"
    CULTURE = "culture", "Culture"
    EDUCATION = "education", "Education"
    WELLNESS = "wellness", "Wellness"
    FOOD = "food", "Food"
    OTHER = "other", "Other"


class Event(TenantScopedModel):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=255)
    cover_image_key = models.CharField(
        max_length=512,
        blank=True,
        help_text="S3 object key for the event cover image.",
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    # Minor units preferred later; Decimal until payments app owns money types.
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(
        max_length=3,
        default="JOD",
        help_text="ISO 4217 currency code for price display.",
    )
    category = models.CharField(
        max_length=64,
        choices=EventCategory.choices,
        blank=True,
        db_index=True,
    )
    capacity = models.PositiveIntegerField(null=True, blank=True)
    is_cancelled = models.BooleanField(default=False)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_events",
    )

    class Meta:
        ordering = ["starts_at", "title"]
        indexes = [
            models.Index(fields=["starts_at"]),
            models.Index(fields=["category", "city_id"]),
            models.Index(fields=["community_id", "starts_at"]),
        ]

    def __str__(self) -> str:
        return self.title


class EventJoinRequest(TenantScopedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="join_requests",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="event_join_requests",
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["event", "user"],
                name="uniq_event_join_request_per_user",
            )
        ]
        indexes = [models.Index(fields=["event", "status"])]

    def __str__(self) -> str:
        return f"{self.user_id} -> {self.event_id} ({self.status})"


class EventTicket(TenantScopedModel):
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="tickets",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="event_tickets",
    )
    token = models.CharField(max_length=512, unique=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    scanned_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text=(
            "Set when the ticket QR/barcode is scanned at the venue on event day. "
            "Only scanned tickets count as attendance for gathering eligibility."
        ),
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["event", "user"],
                name="uniq_event_ticket_per_user",
            )
        ]
        indexes = [models.Index(fields=["event", "user"])]

    def __str__(self) -> str:
        return f"{self.event_id} ticket for {self.user_id}"


class EventNotification(TenantScopedModel):
    class NotificationType(models.TextChoices):
        TICKET = "ticket", "Ticket"
        INVITATION = "invitation", "Invitation"
        UPDATE = "update", "Update"
        CANCELLATION = "cancellation", "Cancellation"

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="event_notifications",
    )
    notification_type = models.CharField(
        max_length=32,
        choices=NotificationType.choices,
        default=NotificationType.TICKET,
        db_index=True,
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    read_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-delivered_at"]

    def __str__(self) -> str:
        return f"{self.notification_type} for {self.user_id} @ {self.event_id}"
