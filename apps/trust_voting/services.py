from __future__ import annotations

import logging
from typing import Tuple
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.trust_voting.models import TrustScore, TrustVote, VotingWindow, AdminTrustFlag
from apps.events.models import Event, EventTicket
from apps.notifications.tasks import send_templated_email_task

logger = logging.getLogger(__name__)


def _compute_event_vote_summary(window: VotingWindow) -> Tuple[int, int, float]:
    """Return (trusted_count, total_count, percent_trusted)"""
    votes = window.votes.all()
    total = votes.count()
    if total == 0:
        return 0, 0, 0.0
    trusted = votes.filter(vote=1).count()
    return trusted, total, trusted / total


@transaction.atomic
def close_voting_window_and_update_scores(window_id: UUID) -> dict:
    window = VotingWindow.objects.select_related().get(pk=window_id)
    if window.is_closed:
        return {}
    trusted, total, percent = _compute_event_vote_summary(window)

    # Resolve event and founder
    try:
        event = Event.all_objects.get(pk=window.event_id)
    except Event.DoesNotExist:
        logger.warning("Event not found when closing voting window: %s", window.event_id)
        window.is_closed = True
        window.save(update_fields=["is_closed"])
        return {}

    founder = event.creator

    # Ensure a TrustScore exists
    trust_score, _ = TrustScore.objects.get_or_create(user=founder, defaults={"score": 0.0, "total_votes": 0})
    previous_score = trust_score.score

    # compute weighted moving average: alpha = new_weight / (old_weight + new_weight)
    # Use older total_votes as weight; new window weight = total
    old_weight = trust_score.total_votes
    new_weight = total
    if old_weight + new_weight == 0:
        new_score = percent
    else:
        new_score = (previous_score * old_weight + percent * new_weight) / (old_weight + new_weight)

    trust_score.score = new_score
    trust_score.total_votes = old_weight + new_weight
    trust_score.last_computed_at = timezone.now()
    trust_score.save(update_fields=["score", "total_votes", "last_computed_at"])

    # Flag big drops (>20 percentage points absolute)
    if previous_score - new_score > 0.20:
        AdminTrustFlag.objects.create(
            user=founder,
            previous_score=previous_score,
            new_score=new_score,
            reason=f"Drop > 20pt after voting window {window.id}",
            community_id=window.community_id,
            city_id=window.city_id,
        )
        # notify admins (simple email to support)
        send_templated_email_task.delay(
            to=settings.EMAIL_SUPPORT_EMAIL,
            subject=f"Trust drop for {founder.full_name}",
            template_basename="admin_trust_alert",
            context={"founder_name": founder.full_name, "previous_score": previous_score, "new_score": new_score},
        )

    # Check minimum threshold: after >=10 votes and percent < 0.4
    if trust_score.total_votes >= 10 and trust_score.score < 0.4:
        AdminTrustFlag.objects.create(
            user=founder,
            previous_score=previous_score,
            new_score=new_score,
            reason="Below 40% after 10+ votes",
            community_id=window.community_id,
            city_id=window.city_id,
        )
        send_templated_email_task.delay(
            to=settings.EMAIL_SUPPORT_EMAIL,
            subject=f"Trust low for {founder.full_name}",
            template_basename="admin_trust_alert",
            context={"founder_name": founder.full_name, "previous_score": previous_score, "new_score": new_score},
        )

    window.is_closed = True
    window.save(update_fields=["is_closed"])

    return {"founder_id": str(founder.id), "previous_score": previous_score, "new_score": new_score, "total_votes": trust_score.total_votes}
