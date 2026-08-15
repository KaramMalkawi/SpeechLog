from __future__ import annotations

from apps.accounts.models import User


class OnboardingStep:
    """Backend-driven next step for mobile/web onboarding orchestration."""

    VERIFY_EMAIL = "verify_email"
    COMPLETE_PROFILE = "complete_profile"
    # Kept for older clients / soft identity nudges later — not a hard gate.
    CONTINUE_ONBOARDING = "continue_onboarding"
    HOME = "home"


def resolve_onboarding_step(user: User) -> str:
    """Return the next onboarding step for a user.

    Source of truth for client routing. Add new steps here as onboarding grows;
    clients map these enums to screens.
    """
    if user.is_platform_admin or user.is_superadmin:
        return OnboardingStep.HOME
    if not user.email_verified:
        return OnboardingStep.VERIFY_EMAIL
    # Soft profile setup after email OTP (photo + bio/location/phone). Skippable.
    # Identity (Didit) verification remains optional and is not a login gate.
    if not user.profile_onboarding_completed:
        return OnboardingStep.COMPLETE_PROFILE
    return OnboardingStep.HOME
