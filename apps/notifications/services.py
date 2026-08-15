from __future__ import annotations

import logging
from typing import Any

import resend
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


class EmailSendError(Exception):
    """Raised when outbound email cannot be sent."""


def _configure_resend() -> None:
    if not settings.RESEND_API_KEY:
        raise EmailSendError("RESEND_API_KEY is not configured.")
    resend.api_key = settings.RESEND_API_KEY


def resolve_logo_url() -> str:
    if not settings.EMAIL_BRAND_LOGO_URL:
        raise EmailSendError(
            "EMAIL_BRAND_LOGO_URL is not configured. "
            "Host the logo at a public HTTPS URL (e.g. on mixedmiles.com)."
        )
    return settings.EMAIL_BRAND_LOGO_URL


def get_base_email_context(**overrides: Any) -> dict[str, Any]:
    website = settings.EMAIL_BRAND_WEBSITE.rstrip("/")
    context = {
        "brand_name": settings.EMAIL_BRAND_NAME,
        "brand_website": f"{website}/",
        "brand_website_display": website.replace("https://", "").replace("http://", ""),
        "logo_url": resolve_logo_url(),
        "support_email": settings.EMAIL_SUPPORT_EMAIL,
        "support_phone": settings.EMAIL_SUPPORT_PHONE,
        "support_location": settings.EMAIL_SUPPORT_LOCATION,
        "colors": settings.EMAIL_BRAND_COLORS,
        "year": timezone.now().year,
        "preheader": "",
    }
    context.update(overrides)
    return context


def render_email_templates(template_basename: str, context: dict[str, Any]) -> tuple[str, str]:
    html = render_to_string(f"emails/{template_basename}.html", context)
    text = render_to_string(f"emails/{template_basename}.txt", context)
    return html, text


def send_templated_email(
    *,
    to: str | list[str],
    subject: str,
    template_basename: str,
    context: dict[str, Any] | None = None,
    tags: list[dict[str, str]] | None = None,
    reply_to: str | None = None,
) -> str:
    recipients = [to] if isinstance(to, str) else list(to)
    if not recipients:
        raise EmailSendError("At least one recipient is required.")

    merged_context = get_base_email_context(**(context or {}))
    html_body, text_body = render_email_templates(template_basename, merged_context)

    _configure_resend()
    params: resend.Emails.SendParams = {
        "from": settings.RESEND_FROM_EMAIL,
        "to": recipients,
        "subject": subject,
        "html": html_body,
        "text": text_body,
        "reply_to": reply_to or settings.EMAIL_SUPPORT_EMAIL,
    }
    if tags:
        params["tags"] = tags

    try:
        response = resend.Emails.send(params)
    except Exception as exc:
        logger.exception("Resend email send failed for template=%s", template_basename)
        raise EmailSendError("Failed to send email.") from exc

    email_id = response.get("id") if isinstance(response, dict) else getattr(response, "id", None)
    if not email_id:
        raise EmailSendError("Resend did not return an email id.")

    logger.info(
        "Email sent template=%s recipients=%s id=%s",
        template_basename,
        recipients,
        email_id,
    )
    return str(email_id)


def send_password_reset_email(
    *,
    to: str,
    reset_url: str,
    recipient_name: str = "",
) -> str:
    display_name = recipient_name.strip() or "there"
    return send_templated_email(
        to=to,
        subject="Reset your Mixed Miles password",
        template_basename="password_reset",
        context={
            "recipient_name": display_name,
            "reset_url": reset_url,
            "preheader": "Use this link to reset your Mixed Miles password. The link expires in 1 hour.",
            "expiry_minutes": settings.PASSWORD_RESET_TIMEOUT // 60,
        },
        tags=[{"name": "category", "value": "password_reset"}],
    )


def send_email_verification_otp(
    *,
    to: str,
    otp: str,
    recipient_name: str = "",
) -> str:
    display_name = recipient_name.strip() or "there"
    expiry_minutes = max(1, settings.EMAIL_OTP_TIMEOUT // 60)
    return send_templated_email(
        to=to,
        subject="Your Mixed Miles verification code",
        template_basename="email_verification_otp",
        context={
            "recipient_name": display_name,
            "otp": otp,
            "preheader": f"Your Mixed Miles verification code is {otp}. It expires in {expiry_minutes} minutes.",
            "expiry_minutes": expiry_minutes,
        },
        tags=[{"name": "category", "value": "email_verification_otp"}],
    )


def send_city_founder_invite_email(
    *,
    to: str,
    temporary_password: str,
    recipient_name: str = "",
    city_name: str = "",
    country_name: str = "",
    login_url: str = "",
) -> str:
    display_name = recipient_name.strip() or "there"
    location = ", ".join(part for part in [city_name, country_name] if part)
    return send_templated_email(
        to=to,
        subject="You're invited to Mixed Miles as a City Founder",
        template_basename="city_founder_invite",
        context={
            "recipient_name": display_name,
            "temporary_password": temporary_password,
            "city_name": city_name,
            "country_name": country_name,
            "location": location or "your city",
            "login_url": login_url or settings.EMAIL_BRAND_WEBSITE.rstrip("/"),
            "preheader": "Your Mixed Miles City Founder account is ready. Sign in with your temporary password.",
        },
        tags=[{"name": "category", "value": "city_founder_invite"}],
    )


def send_platform_admin_invite_email(
    *,
    to: str,
    temporary_password: str,
    recipient_name: str = "",
    login_url: str = "",
    role_label: str = "Admin",
) -> str:
    display_name = recipient_name.strip() or "there"
    return send_templated_email(
        to=to,
        subject=f"You're invited to Mixed Miles as a {role_label}",
        template_basename="platform_admin_invite",
        context={
            "recipient_name": display_name,
            "temporary_password": temporary_password,
            "role_label": role_label,
            "login_url": login_url
            or getattr(settings, "ADMIN_DASHBOARD_URL", "https://admin.mixedmiles.com").rstrip(
                "/"
            ),
            "preheader": f"Your Mixed Miles {role_label} account is ready. Sign in with your temporary password.",
        },
        tags=[{"name": "category", "value": "platform_admin_invite"}],
    )
