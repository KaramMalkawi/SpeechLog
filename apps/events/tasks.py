from __future__ import annotations

from celery import shared_task

from apps.events.services import (
    deliver_event_change_notifications,
    deliver_event_invitation_notification,
    deliver_event_ticket_notification,
)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def deliver_event_ticket_notification_task(self, ticket_id: str) -> str:
    try:
        return deliver_event_ticket_notification(ticket_id)
    except Exception as exc:
        raise self.retry(exc=exc) from exc


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def deliver_event_invitation_notification_task(self, join_request_id: str) -> None:
    try:
        deliver_event_invitation_notification(join_request_id)
    except Exception as exc:
        raise self.retry(exc=exc) from exc


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def deliver_event_change_notifications_task(self, event_id: str, change_type: str) -> int:
    try:
        return deliver_event_change_notifications(event_id, change_type)
    except Exception as exc:
        raise self.retry(exc=exc) from exc
