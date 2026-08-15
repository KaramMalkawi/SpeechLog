from __future__ import annotations

from uuid import UUID

from django.utils.translation import gettext_lazy as _
from rest_framework import authentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

from apps.accounts.models import User
from apps.accounts.services import get_user_for_registration_token
from apps.accounts.tokens import RegistrationAccessToken


class RegistrationJWTAuthentication(authentication.BaseAuthentication):
    """Accepts registration-scoped JWTs for pre-verification endpoints only."""

    www_authenticate_realm = "api"

    def authenticate(self, request: Request):
        header = authentication.get_authorization_header(request).split()
        if not header or header[0].lower() != b"bearer":
            return None

        if len(header) != 2:
            raise AuthenticationFailed(_("Invalid authorization header."))

        try:
            token = RegistrationAccessToken(header[1])
        except Exception as exc:
            raise InvalidToken(_("Invalid registration token.")) from exc

        if token.get("scope") != "registration":
            raise AuthenticationFailed(_("Invalid registration token scope."))

        user_id = token.get("user_id")
        if not user_id:
            raise AuthenticationFailed(_("Invalid registration token."))

        user = get_user_for_registration_token(UUID(user_id))
        return user, token


class VerifiedJWTAuthentication(JWTAuthentication):
    """Standard JWT auth that rejects registration tokens and unverified users."""

    def get_user(self, validated_token):
        if validated_token.get("scope") == "registration":
            raise AuthenticationFailed(_("Registration tokens cannot access this resource."))

        user = super().get_user(validated_token)
        # Identity (Didit) verification is currently optional: email verification is
        # enough to use the API. See apps.accounts.onboarding.resolve_onboarding_step.
        if (
            not user.email_verified
            and not user.is_staff
            and not user.is_platform_admin
            and not user.is_superadmin
        ):
            raise AuthenticationFailed(
                _("Email verification is required to access this resource."),
                code="email_verification_required",
            )
        return user
