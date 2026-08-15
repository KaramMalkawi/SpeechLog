from __future__ import annotations

from datetime import timedelta
from typing import Literal
from uuid import UUID, uuid4

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import TenantScopedModel, UUIDPrimaryKeyModel


class VotingWindow(TenantScopedModel):
    """Represents a voting window for a specific event. Windows are created
    when an event ends + 2h and stay open for 48 hours.
    """

    event_id = models.UUIDField(db_index=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    is_closed = models.BooleanField(default=False)
    prompt_sent = models.BooleanField(default=False)

    class Meta:
        ordering = ["starts_at"]

    def __str__(self) -> str:
        return f"VotingWindow for {self.event_id} ({self.starts_at.isoformat()} - {self.ends_at.isoformat()})"

    @classmethod
    def create_for_event(cls, event) -> "VotingWindow":
        start = event.ends_at + timedelta(hours=2)
        return cls.objects.create(
            event_id=event.id,
            starts_at=start,
            ends_at=start + timedelta(hours=48),
            community_id=event.community_id,
            city_id=event.city_id,
        )


class TrustVote(TenantScopedModel):
    """An attendee's trust vote for the event founder.

    vote: 1 = trusted, 0 = not trusted
    """

    voting_window = models.ForeignKey(
        VotingWindow, on_delete=models.CASCADE, related_name="votes"
    )
    voter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trust_votes")
    vote = models.PositiveSmallIntegerField()  # 1 or 0
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["voting_window", "voter"], name="uniq_vote_per_voter_window")
        ]

    def __str__(self) -> str:
        return f"Vote {self.vote} by {self.voter_id} @ {self.voting_window_id}"


class TrustScore(UUIDPrimaryKeyModel, models.Model):
    """Aggregated founder trust score (0.0 - 1.0)."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trust_score")
    score = models.FloatField(default=0.0)
    last_computed_at = models.DateTimeField(null=True, blank=True)
    total_votes = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Trust score"

    def __str__(self) -> str:
        return f"TrustScore {self.user_id} = {self.score:.3f}"


class AdminTrustFlag(UUIDPrimaryKeyModel, models.Model):
    """Created when a significant drop or low score is detected for review."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trust_flags")
    previous_score = models.FloatField()
    new_score = models.FloatField()
    reason = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"Flag {self.user_id}: {self.previous_score}->{self.new_score} ({self.reason})"
