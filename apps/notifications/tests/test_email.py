from __future__ import annotations

from unittest.mock import patch

import pytest
from django.conf import settings

from apps.notifications.services import (
    EmailSendError,
    get_base_email_context,
    render_email_templates,
    send_password_reset_email,
    send_templated_email,
)


@pytest.mark.django_db
def test_get_base_email_context_includes_brand_details():
    context = get_base_email_context(preheader="Test preheader")

    assert context["brand_name"] == "Mixed Miles"
    assert context["brand_website"] == "https://mixedmiles.com/"
    assert context["support_email"] == "albara@mixedmiles.com"
    assert context["logo_url"] == settings.EMAIL_BRAND_LOGO_URL
    assert context["logo_url"].startswith("https://")
    assert context["colors"]["background"] == "#FFFFFF"


@pytest.mark.django_db
def test_render_password_reset_templates():
    context = get_base_email_context(
        recipient_name="Rami",
        reset_url="https://mixedmiles.com/reset?token=abc",
        expiry_minutes=settings.PASSWORD_RESET_TIMEOUT // 60,
    )
    html, text = render_email_templates("password_reset", context)

    assert "Reset your password" in html
    assert settings.EMAIL_BRAND_LOGO_URL in html
    assert "Rami" in html
    assert "automated message" in html.lower()
    assert "text-align: center" in html


@pytest.mark.django_db
@patch("apps.notifications.services.resend.Emails.send")
def test_send_password_reset_email(mock_send, settings):
    settings.RESEND_API_KEY = "re_test"
    mock_send.return_value = {"id": "email_123"}

    email_id = send_password_reset_email(
        to="test@example.com",
        reset_url="https://mixedmiles.com/reset?token=abc",
        recipient_name="Rami",
    )

    assert email_id == "email_123"
    params = mock_send.call_args.args[0]
    assert settings.EMAIL_BRAND_LOGO_URL in params["html"]
    assert "attachments" not in params


@pytest.mark.django_db
@patch("apps.notifications.services.resend.Emails.send")
def test_send_templated_email_requires_recipient(mock_send):
    with pytest.raises(EmailSendError, match="recipient"):
        send_templated_email(
            to=[],
            subject="Hello",
            template_basename="password_reset",
            context={"recipient_name": "Rami", "reset_url": "https://example.com"},
        )

    mock_send.assert_not_called()
