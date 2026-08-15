from __future__ import annotations

from celery import shared_task


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_city_founder_invite_email_task(
    self,
    *,
    to: str,
    temporary_password: str,
    recipient_name: str = "",
    city_name: str = "",
    country_name: str = "",
    login_url: str = "",
) -> str:
    from apps.notifications.services import EmailSendError, send_city_founder_invite_email

    try:
        return send_city_founder_invite_email(
            to=to,
            temporary_password=temporary_password,
            recipient_name=recipient_name,
            city_name=city_name,
            country_name=country_name,
            login_url=login_url,
        )
    except EmailSendError as exc:
        raise self.retry(exc=exc) from exc


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def sync_founder_applications_task(self) -> dict:
    """Scheduled sync of City Founder form responses (12:00 & 18:00 UTC)."""
    from apps.founders.applications import (
        FounderApplicationSyncError,
        sync_founder_applications_from_sheet,
    )

    try:
        return sync_founder_applications_from_sheet()
    except FounderApplicationSyncError as exc:
        raise self.retry(exc=exc) from exc
