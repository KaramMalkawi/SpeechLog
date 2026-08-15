from __future__ import annotations

from celery import shared_task
from datetime import timedelta
from django.utils import timezone

from apps.trust_voting.models import VotingWindow
from apps.trust_voting.services import close_voting_window_and_update_scores
from apps.events.models import Event


@shared_task(bind=True)
def create_voting_windows_and_send_prompts(self):
    """Scan for events that ended >2h ago and ensure there's a voting window + send prompt."""
    cutoff = timezone.now() - timedelta(hours=2)
    events = Event.all_objects.filter(ends_at__lte=cutoff)
    for event in events:
        # create window if missing
        window_qs = VotingWindow.objects.filter(event_id=event.id)
        if not window_qs.exists():
            window = VotingWindow.create_for_event(event)
        else:
            window = window_qs.first()

        if not window.prompt_sent and window.starts_at <= timezone.now() <= window.ends_at:
            # Send prompt to attendees: use notification service in a simple form
            # We'll mark prompt_sent so it isn't re-sent
            # For delivery we rely on apps.notifications.tasks.send_templated_email_task
            from apps.notifications.tasks import send_templated_email_task

            # gather attendees' emails
            tickets = event.tickets.filter(is_active=True).select_related("user")
            for ticket in tickets:
                if ticket.user.email:
                    send_templated_email_task.delay(
                        to=ticket.user.email,
                        subject=f"Please rate your event: {event.title}",
                        template_basename="trust_vote_prompt",
                        context={"recipient_name": ticket.user.full_name or ticket.user.email, "event_title": event.title, "voting_window_id": str(window.id)},
                    )
            window.prompt_sent = True
            window.save(update_fields=["prompt_sent"])


@shared_task(bind=True)
def close_expired_voting_windows(self):
    now = timezone.now()
    windows = VotingWindow.objects.filter(ends_at__lte=now, is_closed=False)
    for w in windows:
        close_voting_window_and_update_scores(w.id)
