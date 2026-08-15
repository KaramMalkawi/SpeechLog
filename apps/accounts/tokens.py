from datetime import timedelta

from django.conf import settings
from rest_framework_simplejwt.tokens import Token


class RegistrationAccessToken(Token):
    """Short-lived token for completing registration (e.g. identity verification)."""

    token_type = "registration"
    lifetime = timedelta(hours=24)

    @classmethod
    def for_user(cls, user) -> "RegistrationAccessToken":
        token = cls()
        token["user_id"] = str(user.pk)
        token["scope"] = "registration"
        return token


def get_registration_token_lifetime() -> timedelta:
    return getattr(
        settings,
        "REGISTRATION_TOKEN_LIFETIME",
        RegistrationAccessToken.lifetime,
    )
