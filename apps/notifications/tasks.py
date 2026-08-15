from __future__ import annotations

from celery import shared_task

from apps.notifications.services import EmailSendError, send_templated_email


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_templated_email_task(self, **kwargs) -> str:
    try:
        return send_templated_email(**kwargs)
    except EmailSendError as exc:
        raise self.retry(exc=exc) from exc
