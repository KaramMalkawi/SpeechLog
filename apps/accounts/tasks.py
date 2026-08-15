from uuid import UUID

from celery import shared_task

from apps.accounts.didit.services import process_didit_webhook


@shared_task
def process_didit_webhook_task(event_id: str, payload: dict, verification_method: str = "v2") -> None:
    process_didit_webhook(
        event_id=UUID(event_id),
        payload=payload,
        verification_method=verification_method,
    )


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_password_reset_email_task(
    self,
    *,
    to: str,
    reset_url: str,
    recipient_name: str = "",
) -> str:
    from apps.notifications.services import EmailSendError, send_password_reset_email

    try:
        return send_password_reset_email(
            to=to,
            reset_url=reset_url,
            recipient_name=recipient_name,
        )
    except EmailSendError as exc:
        raise self.retry(exc=exc) from exc


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_email_verification_otp_task(
    self,
    *,
    to: str,
    otp: str,
    recipient_name: str = "",
) -> str:
    from apps.notifications.services import EmailSendError, send_email_verification_otp

    try:
        return send_email_verification_otp(
            to=to,
            otp=otp,
            recipient_name=recipient_name,
        )
    except EmailSendError as exc:
        raise self.retry(exc=exc) from exc


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_platform_admin_invite_email_task(
    self,
    *,
    to: str,
    temporary_password: str,
    recipient_name: str = "",
    login_url: str = "",
    role_label: str = "Admin",
) -> str:
    from apps.notifications.services import EmailSendError, send_platform_admin_invite_email

    try:
        return send_platform_admin_invite_email(
            to=to,
            temporary_password=temporary_password,
            recipient_name=recipient_name,
            login_url=login_url,
            role_label=role_label,
        )
    except EmailSendError as exc:
        raise self.retry(exc=exc) from exc
