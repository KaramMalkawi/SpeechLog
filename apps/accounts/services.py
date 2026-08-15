from __future__ import annotations

import secrets
from uuid import UUID

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction
from rest_framework.exceptions import AuthenticationFailed, ValidationError as DRFValidationError

from apps.accounts.models import CommunityMembership, User
from apps.accounts.role_checks import user_can_access_web_dashboard
from apps.accounts.selectors import get_user_by_email, get_user_by_id
from apps.accounts.tokens import RegistrationAccessToken


class IdentityVerificationRequired(AuthenticationFailed):
    status_code = 403
    default_detail = "Identity verification is required before you can sign in."
    default_code = "identity_verification_required"

    def __init__(self, detail=None, code=None, *, user: User | None = None):
        super().__init__(detail=detail, code=code)
        self.user = user


class ManualVerificationRequired(AuthenticationFailed):
    status_code = 403
    default_detail = "Manual admin verification is required before you can sign in."
    default_code = "manual_verification_required"

    def __init__(self, detail=None, code=None, *, user: User | None = None):
        super().__init__(detail=detail, code=code)
        self.user = user


class EmailVerificationRequired(AuthenticationFailed):
    status_code = 403
    default_detail = "Verify your email before you can sign in."
    default_code = "email_verification_required"

    def __init__(self, detail=None, code=None, *, user: User | None = None):
        super().__init__(detail=detail, code=code)
        self.user = user


class PasswordResetRateLimited(Exception):
    """Too many password reset attempts."""


class InvalidPasswordResetToken(Exception):
    """Password reset token is invalid or expired."""


class EmailOTPRateLimited(Exception):
    """Too many email OTP send attempts."""


class EmailOTPInvalid(Exception):
    """Email OTP is invalid, expired, or locked out."""


class EmailAlreadyVerified(Exception):
    """Email has already been verified."""


class RegistrationIncomplete(Exception):
    """Valid credentials but onboarding is not finished — resume with registration token."""

    def __init__(self, *, payload: dict):
        self.payload = payload
        super().__init__(payload.get("detail", "Registration incomplete."))


PASSWORD_RESET_REQUEST_MESSAGE = (
    "If an account exists for that email, you will receive password reset instructions shortly."
)
PASSWORD_RESET_SUCCESS_MESSAGE = "Your password has been reset. You can now sign in."
EMAIL_OTP_SENT_MESSAGE = "If your account needs verification, a code has been sent to your email."
EMAIL_OTP_VERIFIED_MESSAGE = "Email verified successfully."


def _password_reset_cache_key(token: str) -> str:
    return f"password_reset:{token}"


def _rate_limit_cache_key(scope: str, value: str) -> str:
    return f"password_reset_rate:{scope}:{value}"


def _increment_rate_limit(*, scope: str, value: str, limit: int, period: int) -> None:
    if not value:
        return

    key = _rate_limit_cache_key(scope, value)
    current = cache.get(key)
    if current is not None and int(current) >= limit:
        raise PasswordResetRateLimited()

    new_count = (int(current) if current else 0) + 1
    cache.set(key, new_count, timeout=period)


def _enforce_password_reset_rate_limits(*, email: str, request_ip: str | None) -> None:
    period = settings.PASSWORD_RESET_RATE_LIMIT_PERIOD
    _increment_rate_limit(
        scope="email",
        value=User.objects.normalize_email(email),
        limit=settings.PASSWORD_RESET_EMAIL_RATE_LIMIT,
        period=period,
    )
    _increment_rate_limit(
        scope="ip",
        value=request_ip or "unknown",
        limit=settings.PASSWORD_RESET_IP_RATE_LIMIT,
        period=period,
    )


def build_password_reset_url(token: str) -> str:
    base_url = settings.PASSWORD_RESET_FRONTEND_URL.rstrip("/")
    return f"{base_url}?token={token}"


def _issue_password_reset_token(user: User) -> str:
    token = secrets.token_urlsafe(32)
    cache.set(
        _password_reset_cache_key(token),
        str(user.pk),
        timeout=settings.PASSWORD_RESET_TIMEOUT,
    )
    return token


def _consume_password_reset_token(token: str) -> User:
    if not token:
        raise InvalidPasswordResetToken()

    cache_key = _password_reset_cache_key(token)
    user_id = cache.get(cache_key)
    if not user_id:
        raise InvalidPasswordResetToken()

    cache.delete(cache_key)

    try:
        user = User.objects.get(pk=UUID(str(user_id)))
    except (User.DoesNotExist, ValueError) as exc:
        raise InvalidPasswordResetToken() from exc

    if not user.is_active:
        raise InvalidPasswordResetToken()

    return user


@transaction.atomic
def apply_user_role(user: User, role: str, *, save: bool = True) -> User:
    """Set product role and keep Django access flags aligned.

    Product ACL is ``User.role`` + DRF permission classes (see 030-roles-permissions).
    Django Groups/Permissions are not used for product auth.

    - Superadmin (``is_superuser``): keeps staff/superuser; role still updates.
    - Everyone else: ``is_staff=False``, no groups, no user_permissions.
    """
    if role not in User.Role.values:
        raise ValueError(f"Invalid role: {role}")

    user.role = role
    updates = ["role", "updated_at"]

    if user.is_superuser:
        # Superadmin retains full Django admin access.
        if not user.is_staff:
            user.is_staff = True
            updates.append("is_staff")
        if save:
            user.save(update_fields=list(dict.fromkeys(updates)))
        return user

    if user.is_staff:
        user.is_staff = False
        updates.append("is_staff")

    if save:
        user.save(update_fields=list(dict.fromkeys(updates)))
        user.groups.clear()
        user.user_permissions.clear()
    return user


def clear_django_access_for_non_superusers() -> int:
    """One-shot cleanup: strip staff + Django perms from non-superusers."""
    qs = User.objects.filter(is_superuser=False)
    updated = qs.filter(is_staff=True).update(is_staff=False)
    for user in qs.iterator():
        if user.groups.exists() or user.user_permissions.exists():
            user.groups.clear()
            user.user_permissions.clear()
            updated += 1
    return updated


@transaction.atomic
def register_user(
    *,
    full_name: str,
    email: str,
    password: str,
    request_ip: str | None = None,
) -> User:
    """Create an unverified account from name, email, and password.

    Sends a hashed email OTP for ownership verification. Nationality, residence
    country, and phone number are collected in later registration steps.
    """
    normalized_email = User.objects.normalize_email(email)
    if User.objects.filter(email=normalized_email).exists():
        raise ValueError("A user with this email already exists.")

    cleaned_name = full_name.strip()
    if not cleaned_name:
        raise ValueError("Full name is required.")

    user = User(
        email=normalized_email,
        full_name=cleaned_name,
        verification_status=User.VerificationStatus.UNVERIFIED,
        email_verified=False,
        registration_step=1,
    )
    user.set_password(password)
    user.save()
    user = apply_user_role(user, User.Role.NON_MEMBER)
    request_email_verification_otp(user=user, request_ip=request_ip)
    return user


def issue_registration_token(user: User) -> str:
    return str(RegistrationAccessToken.for_user(user))


def _email_otp_cache_key(user_id: UUID | str) -> str:
    return f"email_otp:{user_id}"


def _email_otp_rate_limit_cache_key(*, scope: str, value: str) -> str:
    return f"email_otp_rate:{scope}:{value}"


def _generate_email_otp() -> str:
    length = settings.EMAIL_OTP_LENGTH
    # Cryptographically secure numeric OTP; never log or persist plaintext.
    return "".join(secrets.choice("0123456789") for _ in range(length))


def _hash_email_otp(otp: str) -> str:
    """Hash OTP with Argon2 (same hasher stack as passwords). Never store plaintext."""
    from django.contrib.auth.hashers import make_password

    return make_password(otp)


def _check_email_otp(*, otp: str, digest: str) -> bool:
    from django.contrib.auth.hashers import check_password

    return check_password(otp, digest)


def _enforce_email_otp_send_rate_limits(*, email: str, request_ip: str | None) -> None:
    period = settings.EMAIL_OTP_RATE_LIMIT_PERIOD
    email_key = _email_otp_rate_limit_cache_key(
        scope="email",
        value=User.objects.normalize_email(email),
    )
    ip_key = _email_otp_rate_limit_cache_key(scope="ip", value=request_ip or "unknown")

    for key, limit in (
        (email_key, settings.EMAIL_OTP_EMAIL_RATE_LIMIT),
        (ip_key, settings.EMAIL_OTP_IP_RATE_LIMIT),
    ):
        current = cache.get(key)
        if current is not None and int(current) >= limit:
            raise EmailOTPRateLimited()
        new_count = (int(current) if current else 0) + 1
        cache.set(key, new_count, timeout=period)


def issue_email_verification_otp(*, user: User) -> str:
    """Create a new OTP, store only its Argon2 digest in Redis, return plaintext once."""
    import time

    otp = _generate_email_otp()
    timeout = settings.EMAIL_OTP_TIMEOUT
    cache.set(
        _email_otp_cache_key(user.pk),
        {
            "digest": _hash_email_otp(otp),
            "attempts": 0,
            "expires_at": time.time() + timeout,
        },
        timeout=timeout,
    )
    return otp


def request_email_verification_otp(*, user: User, request_ip: str | None = None) -> None:
    """Rate-limit, issue OTP, and enqueue email delivery via Celery."""
    if user.email_verified:
        raise EmailAlreadyVerified()

    _enforce_email_otp_send_rate_limits(email=user.email, request_ip=request_ip)

    from apps.accounts.tasks import send_email_verification_otp_task

    otp = issue_email_verification_otp(user=user)
    send_email_verification_otp_task.delay(
        to=user.email,
        otp=otp,
        recipient_name=user.full_name.strip(),
    )


@transaction.atomic
def verify_email_otp(*, user: User, otp: str) -> User:
    """Validate OTP with constant-time hasher check; mark email verified on success."""
    import time

    if user.email_verified:
        raise EmailAlreadyVerified()

    cleaned = (otp or "").strip()
    if not cleaned.isdigit() or len(cleaned) != settings.EMAIL_OTP_LENGTH:
        raise EmailOTPInvalid("Enter the 6-digit code from your email.")

    cache_key = _email_otp_cache_key(user.pk)
    payload = cache.get(cache_key)
    if not payload or not isinstance(payload, dict) or "digest" not in payload:
        raise EmailOTPInvalid("This code has expired. Request a new one.")

    attempts = int(payload.get("attempts") or 0)
    if attempts >= settings.EMAIL_OTP_MAX_ATTEMPTS:
        cache.delete(cache_key)
        raise EmailOTPInvalid("Too many incorrect attempts. Request a new code.")

    if not _check_email_otp(otp=cleaned, digest=payload["digest"]):
        payload["attempts"] = attempts + 1
        if payload["attempts"] >= settings.EMAIL_OTP_MAX_ATTEMPTS:
            cache.delete(cache_key)
            raise EmailOTPInvalid("Too many incorrect attempts. Request a new code.")
        expires_at = float(payload.get("expires_at") or 0)
        remaining = int(expires_at - time.time())
        if remaining <= 0:
            cache.delete(cache_key)
            raise EmailOTPInvalid("This code has expired. Request a new one.")
        cache.set(cache_key, payload, timeout=remaining)
        raise EmailOTPInvalid("Invalid verification code.")

    cache.delete(cache_key)
    user.email_verified = True
    user.save(update_fields=["email_verified", "updated_at"])
    return ensure_user_has_active_community(user=user)


def ensure_user_has_active_community(*, user: User) -> User:
    """Assign a default community when the user has none.

    Gatherings/events require community tenant context. Until city/community
    selection is part of onboarding, email-verified users land in the default
    GENERAL community (see ``DEFAULT_COMMUNITY_SLUG``).
    """
    from apps.tenancy.selectors import get_community_by_id, get_default_community

    if user.active_community_id:
        community = get_community_by_id(user.active_community_id)
        if community is not None:
            CommunityMembership.all_objects.get_or_create(
                user=user,
                community_id=community.id,
                defaults={
                    "city_id": community.city_id,
                    "role": CommunityMembership.Role.MEMBER,
                },
            )
            return user

    community = get_default_community()
    if community is None:
        return user

    CommunityMembership.all_objects.get_or_create(
        user=user,
        community_id=community.id,
        defaults={
            "city_id": community.city_id,
            "role": CommunityMembership.Role.MEMBER,
        },
    )
    if user.active_community_id != community.id:
        user.active_community_id = community.id
        user.save(update_fields=["active_community_id", "updated_at"])
    return user


def authenticate_verified_user(*, email: str, password: str) -> User:
    user = authenticate(username=email, password=password)
    if user is None:
        raise AuthenticationFailed("Invalid email or password.")
    if not user.is_active:
        raise AuthenticationFailed("This account is inactive.")
    if user.is_platform_admin:
        return user
    if not user.email_verified:
        raise EmailVerificationRequired(user=user)
    # Identity (Didit) verification and manual admin review are currently optional
    # for mobile login/onboarding — email verification alone is enough to sign in.
    # These checks will resurface later as soft, per-action recommendations rather
    # than a hard login gate.
    return ensure_user_has_active_community(user=user)


def authenticate_admin_user(*, email: str, password: str) -> User:
    """Authenticate for the admin dashboard — Admin role or Django superuser."""
    user = authenticate(username=email, password=password)
    if user is None:
        raise AuthenticationFailed("Invalid email or password.")
    if not user.is_active:
        raise AuthenticationFailed("This account is inactive.")
    if not (user.is_platform_admin or user.is_superadmin):
        raise AuthenticationFailed("Only administrators can sign in here.")
    return user


def authenticate_dashboard_user(*, email: str, password: str) -> User:
    """Authenticate for the web dashboard — Admin, City Founder, or superuser."""
    user = authenticate(username=email, password=password)
    if user is None:
        raise AuthenticationFailed("Invalid email or password.")
    if not user.is_active:
        raise AuthenticationFailed("This account is inactive.")
    if not user_can_access_web_dashboard(user):
        raise AuthenticationFailed(
            "Only Admin and City Founder accounts can sign in here."
        )

    if user.role == User.Role.CITY_FOUNDER:
        from apps.founders.models import Founder

        founder = Founder.objects.filter(user_id=user.pk).first()
        if founder is None:
            raise AuthenticationFailed("City Founder profile not found.")
        if founder.status not in {
            Founder.Status.PENDING_FIRST_LOGIN,
            Founder.Status.ACTIVE,
        }:
            raise AuthenticationFailed("This City Founder account is not active.")

    if user.is_platform_admin or user.is_superadmin:
        return user

    if not user.is_identity_verified:
        raise IdentityVerificationRequired()
    return user


def get_user_for_registration_token(user_id: UUID) -> User:
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist as exc:
        raise AuthenticationFailed("Invalid registration token.") from exc

    if not user.is_active:
        raise AuthenticationFailed("This account is inactive.")
    if user.email_verified:
        raise AuthenticationFailed("Account is already verified. Please sign in.")
    return user


def mark_user_verified(user: User) -> User:
    user.verification_status = User.VerificationStatus.VERIFIED
    user.email_verified = True
    user.registration_step = 2
    user.save(
        update_fields=[
            "verification_status",
            "email_verified",
            "registration_step",
            "updated_at",
        ]
    )
    return user


def generate_temporary_password(*, length: int = 14) -> str:
    """Generate a password that satisfies Django's AUTH_PASSWORD_VALIDATORS."""
    import secrets
    import string

    from django.contrib.auth.password_validation import validate_password
    from django.core.exceptions import ValidationError

    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    for _ in range(50):
        password = (
            secrets.choice(string.ascii_uppercase)
            + secrets.choice(string.ascii_lowercase)
            + secrets.choice(string.digits)
            + secrets.choice("!@#$%^&*")
            + "".join(secrets.choice(alphabet) for _ in range(max(length - 4, 8)))
        )
        try:
            validate_password(password)
            return password
        except ValidationError:
            continue
    raise RuntimeError("Unable to generate a valid temporary password.")


def _provision_dashboard_user(
    *,
    full_name: str,
    email: str,
    password: str,
    role: str,
) -> User:
    """Create a verified dashboard account that must change password on first login."""
    normalized_email = User.objects.normalize_email(email)
    if User.objects.filter(email=normalized_email).exists():
        raise ValueError("A user with this email already exists.")

    user = User(
        email=normalized_email,
        full_name=full_name.strip(),
        verification_status=User.VerificationStatus.VERIFIED,
        registration_step=2,
        manual_verification_approved=True,
        email_verified=True,
        is_active=True,
        must_change_password=True,
    )
    user.set_password(password)
    user.save()
    return apply_user_role(user, role)


@transaction.atomic
def provision_city_founder_user(
    *,
    full_name: str,
    email: str,
    password: str,
) -> User:
    """Create a verified City Founder account for admin provisioning."""
    return _provision_dashboard_user(
        full_name=full_name,
        email=email,
        password=password,
        role=User.Role.CITY_FOUNDER,
    )


@transaction.atomic
def provision_platform_admin_user(
    *,
    full_name: str,
    email: str,
    password: str,
) -> User:
    """Create a verified Platform Admin account for admin provisioning."""
    return _provision_dashboard_user(
        full_name=full_name,
        email=email,
        password=password,
        role=User.Role.ADMIN,
    )


def email_is_taken(*, email: str, exclude_user_id: UUID | None = None) -> bool:
    normalized = User.objects.normalize_email(email)
    qs = User.objects.filter(email=normalized)
    if exclude_user_id is not None:
        qs = qs.exclude(pk=exclude_user_id)
    return qs.exists()


def update_user_account_fields(
    *,
    user_id: UUID,
    full_name: str | None = None,
    email: str | None = None,
    is_active: bool | None = None,
) -> User:
    user = User.objects.get(pk=user_id)
    updates: list[str] = []
    if full_name is not None:
        user.full_name = full_name.strip()
        updates.append("full_name")
    if email is not None:
        normalized = User.objects.normalize_email(email)
        if email_is_taken(email=normalized, exclude_user_id=user.id):
            raise ValueError("A user with this email already exists.")
        user.email = normalized
        updates.append("email")
    if is_active is not None:
        user.is_active = is_active
        updates.append("is_active")
    if updates:
        updates.append("updated_at")
        user.save(update_fields=list(dict.fromkeys(updates)))
    return user


def delete_user_account(*, user_id: UUID) -> None:
    User.objects.filter(pk=user_id).delete()


class AdminUserDeleteError(Exception):
    """Raised when an admin user delete is not allowed."""


class AdminUserUpdateError(Exception):
    """Raised when an admin user update is not allowed."""


def admin_user_to_payload(user: User, *, actor_id: UUID | str | None = None) -> dict:
    from apps.founders.selectors import get_city_founder_by_user_id
    from apps.tenancy.country_data import get_country_by_code
    from apps.tenancy.selectors import get_city_by_id

    country = (
        get_country_by_code(user.residence_country_code)
        if user.residence_country_code
        else None
    )
    can_edit = not user.is_superuser and (
        actor_id is None or str(user.id) != str(actor_id)
    )
    # Allow editing own name/email/password but not own role — exposed as can_edit_self
    can_edit_self = not user.is_superuser and (
        actor_id is not None and str(user.id) == str(actor_id)
    )
    payload = {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "is_superuser": user.is_superuser,
        "is_active": user.is_active,
        "must_change_password": user.must_change_password,
        "phone_number": user.phone_number or "",
        "created_at": user.created_at,
        "residence_country_code": user.residence_country_code or "",
        "residence_country_name": country.name if country else "",
        "is_current_user": str(user.id) == str(actor_id) if actor_id is not None else False,
        "can_delete": can_edit,
        "can_edit": can_edit or can_edit_self,
        "can_edit_role": can_edit,
        "founder_id": None,
        "city_id": None,
        "city_name": "",
        "country_id": None,
        "country_name": "",
        "country_code": "",
        "founder_status": "",
        "gathering_attendance_credit": int(
            getattr(user, "gathering_attendance_credit", 0) or 0
        ),
        "bypass_gathering_attendance": bool(
            getattr(user, "bypass_gathering_attendance", False)
        ),
        "events_scanned": 0,
    }
    try:
        from apps.events.selectors import count_attended_events

        payload["events_scanned"] = count_attended_events(user_id=user.id)
    except Exception:
        payload["events_scanned"] = 0

    if user.role == User.Role.CITY_FOUNDER:
        founder = None
        try:
            founder = user.founder_profile
        except ObjectDoesNotExist:
            founder = get_city_founder_by_user_id(user.id)
        if founder is not None:
            city = get_city_by_id(founder.city_id)
            payload.update(
                {
                    "founder_id": founder.id,
                    "city_id": founder.city_id,
                    "city_name": city.name if city else "",
                    "country_id": city.country_id if city else None,
                    "country_name": city.country.name if city else "",
                    "country_code": city.country.code if city else "",
                    "founder_status": founder.status,
                }
            )
    return payload


@transaction.atomic
def update_user_by_admin(
    *,
    actor_id: UUID | str,
    user_id: UUID,
    full_name: str | None = None,
    email: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
    phone_number: str | None = None,
    residence_country_code: str | None = None,
    city_id: UUID | None = None,
    founder_status: str | None = None,
    reset_password: bool = False,
    gathering_attendance_credit: int | None = None,
    bypass_gathering_attendance: bool | None = None,
) -> tuple[User, str | None]:
    """Comprehensive admin update. Returns (user, temporary_password_or_none)."""
    from apps.adminpanel.services import (
        USER_ROLE_UPDATE_ACTION,
        record_admin_audit_event,
    )
    from apps.founders.services import (
        assign_or_update_founder_for_user,
        deactivate_founder_profile_for_user,
    )
    from apps.tenancy.country_data import get_country_by_code

    target = get_user_by_id(user_id)
    if target is None:
        raise AdminUserUpdateError("User not found.")

    if target.is_superuser:
        raise AdminUserUpdateError("Superadmin accounts cannot be edited here.")

    is_self = str(target.id) == str(actor_id)
    if is_self and role is not None and role != target.role:
        raise AdminUserUpdateError("You cannot change your own role.")
    if is_self and is_active is False:
        raise AdminUserUpdateError("You cannot deactivate your own account.")

    if role is not None and role not in User.Role.values:
        raise AdminUserUpdateError("Invalid role.")

    if role == User.Role.CITY_FOUNDER or (
        role is None and target.role == User.Role.CITY_FOUNDER
    ):
        effective_role = role or target.role
        if effective_role == User.Role.CITY_FOUNDER and city_id is None and (
            role == User.Role.CITY_FOUNDER and target.role != User.Role.CITY_FOUNDER
        ):
            raise DRFValidationError(
                {"city_id": "Select a city when assigning the City Founder role."}
            )

    previous_role = target.role
    temporary_password: str | None = None

    if full_name is not None or email is not None or is_active is not None:
        try:
            target = update_user_account_fields(
                user_id=target.id,
                full_name=full_name,
                email=email,
                is_active=is_active,
            )
        except ValueError as exc:
            raise DRFValidationError({"email": str(exc)}) from exc

    field_updates: list[str] = []
    if phone_number is not None:
        target.phone_number = phone_number.strip()
        field_updates.append("phone_number")
    if residence_country_code is not None:
        code = residence_country_code.strip().upper()
        if code and get_country_by_code(code) is None:
            raise DRFValidationError(
                {"residence_country_code": "Unknown residence country code."}
            )
        if code and code not in settings.RESIDENCE_COUNTRY_CODES:
            raise DRFValidationError(
                {"residence_country_code": "Selected country is not available for residence."}
            )
        target.residence_country_code = code
        field_updates.append("residence_country_code")
    if field_updates:
        field_updates.append("updated_at")
        target.save(update_fields=list(dict.fromkeys(field_updates)))

    attendance_updates: list[str] = []
    if gathering_attendance_credit is not None:
        if gathering_attendance_credit < 0 or gathering_attendance_credit > 99:
            raise DRFValidationError(
                {
                    "gathering_attendance_credit": (
                        "Attendance credit must be between 0 and 99."
                    )
                }
            )
        target.gathering_attendance_credit = gathering_attendance_credit
        attendance_updates.append("gathering_attendance_credit")
    if bypass_gathering_attendance is not None:
        target.bypass_gathering_attendance = bypass_gathering_attendance
        attendance_updates.append("bypass_gathering_attendance")
    if attendance_updates:
        attendance_updates.append("updated_at")
        target.save(update_fields=list(dict.fromkeys(attendance_updates)))

    if role is not None and role != previous_role:
        if previous_role == User.Role.CITY_FOUNDER and role != User.Role.CITY_FOUNDER:
            deactivate_founder_profile_for_user(user_id=target.id)
        apply_user_role(target, role)
        record_admin_audit_event(
            actor_id=actor_id,
            action=USER_ROLE_UPDATE_ACTION,
            metadata={
                "user_id": str(target.id),
                "email": target.email,
                "previous_role": previous_role,
                "new_role": role,
            },
        )
        target.refresh_from_db()

    if target.role == User.Role.CITY_FOUNDER:
        founder_city_id = city_id
        if founder_city_id is None:
            from apps.founders.selectors import get_city_founder_by_user_id

            existing = get_city_founder_by_user_id(target.id)
            founder_city_id = existing.city_id if existing else None
        if founder_city_id is None:
            raise DRFValidationError(
                {"city_id": "Select a city for this City Founder."}
            )
        assign_or_update_founder_for_user(
            actor_id=actor_id,
            user_id=target.id,
            city_id=founder_city_id,
            status=founder_status,
        )
        if is_active is None and founder_status == "suspended":
            target = update_user_account_fields(user_id=target.id, is_active=False)
        elif founder_status and founder_status != "suspended" and not target.is_active:
            # Reactivate account when founder status leaves suspended, unless explicitly inactive
            if is_active is not False:
                target = update_user_account_fields(user_id=target.id, is_active=True)

    if reset_password:
        temporary_password = generate_temporary_password()
        target.set_password(temporary_password)
        target.must_change_password = True
        target.save(update_fields=["password", "must_change_password", "updated_at"])

    target.refresh_from_db()
    return target, temporary_password


@transaction.atomic
def update_user_role_by_admin(
    *,
    actor_id: UUID | str,
    user_id: UUID,
    role: str,
) -> User:
    """Change a user's role (admin action). Syncs permissions via apply_user_role."""
    user, _ = update_user_by_admin(actor_id=actor_id, user_id=user_id, role=role)
    return user


@transaction.atomic
def delete_user_by_admin(
    *,
    actor_id: UUID | str,
    user_id: UUID,
    confirmation_name: str,
) -> None:
    from apps.adminpanel.services import USER_DELETE_ACTION, record_admin_audit_event

    target = get_user_by_id(user_id)
    if target is None:
        raise AdminUserDeleteError("User not found.")

    if str(target.id) == str(actor_id):
        raise AdminUserDeleteError("You cannot delete your own account.")

    if target.is_superuser:
        raise AdminUserDeleteError("Superadmin accounts cannot be deleted.")

    expected = (target.full_name or "").strip()
    if confirmation_name.strip() != expected:
        raise AdminUserDeleteError("Type the user's full name exactly to confirm deletion.")

    metadata = {
        "user_id": str(target.id),
        "email": target.email,
        "full_name": target.full_name,
        "role": target.role,
    }
    delete_user_account(user_id=target.id)
    record_admin_audit_event(
        actor_id=actor_id,
        action=USER_DELETE_ACTION,
        metadata=metadata,
    )


@transaction.atomic
def change_own_password(
    *,
    user_id: UUID,
    current_password: str,
    new_password: str,
) -> User:
    """Authenticated member/non-member voluntary password change (mobile app)."""
    user = User.objects.get(pk=user_id)

    if not user.check_password(current_password):
        raise ValueError("Current password is incorrect.")

    if current_password == new_password:
        raise ValueError("New password must be different from your current password.")

    try:
        validate_password(new_password, user=user)
    except ValidationError as exc:
        raise ValueError("; ".join(exc.messages)) from exc

    user.set_password(new_password)
    user.must_change_password = False
    user.save(update_fields=["password", "must_change_password", "updated_at"])
    return user


@transaction.atomic
def change_founder_password(
    *,
    user_id: UUID,
    current_password: str,
    new_password: str,
) -> User:
    """City Founder first-login (or voluntary) password change."""
    user = User.objects.get(pk=user_id)
    if user.role != User.Role.CITY_FOUNDER:
        raise ValueError("Only City Founder accounts can use this endpoint.")

    if not user.check_password(current_password):
        raise ValueError("Current password is incorrect.")

    if current_password == new_password:
        raise ValueError("New password must be different from your current password.")

    try:
        validate_password(new_password, user=user)
    except ValidationError as exc:
        raise ValueError("; ".join(exc.messages)) from exc

    user.set_password(new_password)
    user.must_change_password = False
    user.save(update_fields=["password", "must_change_password", "updated_at"])

    from apps.founders.services import mark_founder_active_after_first_login

    mark_founder_active_after_first_login(user_id=user.id)
    return user


@transaction.atomic
def change_dashboard_password(
    *,
    user_id: UUID,
    current_password: str,
    new_password: str,
) -> User:
    """Platform Admin / Superadmin voluntary password change from Settings."""
    from apps.adminpanel.services import PASSWORD_CHANGE_ACTION, record_admin_audit_event

    user = User.objects.get(pk=user_id)
    if not (user.is_platform_admin or user.is_superuser):
        raise ValueError("Only Admin accounts can use this endpoint.")

    if not user.check_password(current_password):
        raise ValueError("Current password is incorrect.")

    if current_password == new_password:
        raise ValueError("New password must be different from your current password.")

    try:
        validate_password(new_password, user=user)
    except ValidationError as exc:
        raise ValueError("; ".join(exc.messages)) from exc

    user.set_password(new_password)
    user.must_change_password = False
    user.save(update_fields=["password", "must_change_password", "updated_at"])

    record_admin_audit_event(
        actor_id=user.id,
        action=PASSWORD_CHANGE_ACTION,
        metadata={"email": user.email},
    )
    return user


@transaction.atomic
def update_dashboard_profile(
    *,
    user_id: UUID,
    full_name: str,
) -> User:
    """Platform Admin / Superadmin updates display name from Settings."""
    from apps.adminpanel.services import PROFILE_UPDATE_ACTION, record_admin_audit_event

    user = User.objects.get(pk=user_id)
    if not (user.is_platform_admin or user.is_superuser):
        raise ValueError("Only Admin accounts can use this endpoint.")

    cleaned = full_name.strip()
    if not cleaned:
        raise ValueError("Full name is required.")
    if len(cleaned) > 160:
        raise ValueError("Full name must be 160 characters or fewer.")

    if user.full_name == cleaned:
        return user

    user.full_name = cleaned
    user.save(update_fields=["full_name", "updated_at"])

    record_admin_audit_event(
        actor_id=user.id,
        action=PROFILE_UPDATE_ACTION,
        metadata={"email": user.email, "full_name": cleaned},
    )
    return user


class PlatformAdminNotFound(Exception):
    """Platform admin user does not exist."""


class PlatformAdminDeleteConfirmationError(Exception):
    """Delete confirmation name does not match."""


class PlatformAdminUpdateError(Exception):
    """Raised when a platform admin update is not allowed."""


PLATFORM_ADMIN_STATUSES = frozenset({"pending_first_login", "active", "suspended"})


def platform_admin_status(user: User) -> str:
    if not user.is_active:
        return "suspended"
    if user.must_change_password:
        return "pending_first_login"
    return "active"


def platform_admin_to_payload(user: User, *, actor_id: UUID | str | None = None) -> dict:
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "status": platform_admin_status(user),
        "is_superuser": user.is_superuser,
        "is_active": user.is_active,
        "must_change_password": user.must_change_password,
        "created_at": user.created_at,
        "is_current_user": str(user.id) == str(actor_id) if actor_id is not None else False,
        "can_delete": not user.is_superuser
        and (actor_id is None or str(user.id) != str(actor_id)),
        "can_edit": not user.is_superuser
        and (actor_id is None or str(user.id) != str(actor_id)),
    }


@transaction.atomic
def create_user_by_admin(
    *,
    actor_id: UUID | str,
    full_name: str,
    email: str,
    role: str,
    city_id: UUID | None = None,
) -> tuple[User, str]:
    """Provision any product role except Superadmin (not a creatable role)."""
    from apps.adminpanel.services import ADMIN_CREATE_ACTION, record_admin_audit_event

    if role not in User.Role.values:
        raise DRFValidationError({"role": "Invalid role."})

    if role == User.Role.CITY_FOUNDER:
        from apps.founders.services import create_city_founder

        if city_id is None:
            raise DRFValidationError({"city_id": "Select a city when creating a City Founder."})
        founder, temporary_password = create_city_founder(
            actor_id=actor_id,
            full_name=full_name,
            email=email,
            city_id=city_id,
        )
        return founder.user, temporary_password

    if email_is_taken(email=email):
        raise DRFValidationError({"email": "A user with this email already exists."})

    temporary_password = generate_temporary_password()
    try:
        user = _provision_dashboard_user(
            full_name=full_name,
            email=email,
            password=temporary_password,
            role=role,
        )
    except ValueError as exc:
        raise DRFValidationError({"email": str(exc)}) from exc

    record_admin_audit_event(
        actor_id=actor_id,
        action=ADMIN_CREATE_ACTION,
        metadata={
            "user_id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
        },
    )
    return user, temporary_password


@transaction.atomic
def create_platform_admin(
    *,
    actor_id: UUID | str,
    full_name: str,
    email: str,
) -> tuple[User, str]:
    from apps.adminpanel.services import ADMIN_CREATE_ACTION, record_admin_audit_event

    if email_is_taken(email=email):
        raise DRFValidationError({"email": "A user with this email already exists."})

    temporary_password = generate_temporary_password()
    try:
        user = provision_platform_admin_user(
            full_name=full_name,
            email=email,
            password=temporary_password,
        )
    except ValueError as exc:
        raise DRFValidationError({"email": str(exc)}) from exc

    record_admin_audit_event(
        actor_id=actor_id,
        action=ADMIN_CREATE_ACTION,
        metadata={
            "user_id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "status": platform_admin_status(user),
        },
    )
    return user, temporary_password


@transaction.atomic
def update_platform_admin(
    *,
    actor_id: UUID | str,
    user_id: UUID,
    full_name: str | None = None,
    email: str | None = None,
    status: str | None = None,
) -> User:
    from apps.adminpanel.services import ADMIN_UPDATE_ACTION, record_admin_audit_event

    target = get_user_by_id(user_id)
    if target is None or not (target.is_platform_admin or target.is_superuser):
        raise PlatformAdminNotFound()

    if target.is_superuser:
        raise PlatformAdminUpdateError("Superadmin accounts cannot be edited here.")

    if str(target.id) == str(actor_id):
        raise PlatformAdminUpdateError("You cannot edit your own admin account here.")

    is_active: bool | None = None
    must_change_password: bool | None = None
    if status is not None:
        if status not in PLATFORM_ADMIN_STATUSES:
            raise DRFValidationError({"status": "Invalid status."})
        if status == "suspended":
            is_active = False
        elif status == "active":
            is_active = True
            must_change_password = False
        elif status == "pending_first_login":
            is_active = True
            must_change_password = True

    try:
        user = update_user_account_fields(
            user_id=target.id,
            full_name=full_name,
            email=email,
            is_active=is_active,
        )
    except ValueError as exc:
        raise DRFValidationError({"email": str(exc)}) from exc

    if must_change_password is not None and user.must_change_password != must_change_password:
        user.must_change_password = must_change_password
        user.save(update_fields=["must_change_password", "updated_at"])

    record_admin_audit_event(
        actor_id=actor_id,
        action=ADMIN_UPDATE_ACTION,
        metadata={
            "user_id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "status": platform_admin_status(user),
        },
    )
    return user


@transaction.atomic
def delete_platform_admin(
    *,
    actor_id: UUID | str,
    user_id: UUID,
    confirmation_name: str,
) -> None:
    from apps.adminpanel.services import ADMIN_DELETE_ACTION, record_admin_audit_event

    target = get_user_by_id(user_id)
    if target is None or not (target.is_platform_admin or target.is_superuser):
        raise PlatformAdminNotFound()

    if target.is_superuser:
        raise PlatformAdminDeleteConfirmationError("Superadmin accounts cannot be deleted.")

    if str(target.id) == str(actor_id):
        raise PlatformAdminDeleteConfirmationError("You cannot delete your own account.")

    expected = (target.full_name or "").strip()
    if confirmation_name.strip() != expected:
        raise PlatformAdminDeleteConfirmationError(
            "Type the admin's full name exactly to confirm deletion."
        )

    metadata = {
        "user_id": str(target.id),
        "email": target.email,
        "full_name": target.full_name,
        "status": platform_admin_status(target),
    }
    delete_user_account(user_id=target.id)
    record_admin_audit_event(
        actor_id=actor_id,
        action=ADMIN_DELETE_ACTION,
        metadata=metadata,
    )


def request_password_reset(*, email: str, request_ip: str | None = None) -> None:
    _enforce_password_reset_rate_limits(email=email, request_ip=request_ip)

    user = get_user_by_email(email)
    if user is None or not user.is_active:
        return

    from apps.accounts.tasks import send_password_reset_email_task

    token = _issue_password_reset_token(user)
    send_password_reset_email_task.delay(
        to=user.email,
        reset_url=build_password_reset_url(token),
        recipient_name=user.full_name.strip(),
    )


@transaction.atomic
def confirm_password_reset(*, token: str, new_password: str) -> User:
    user = _consume_password_reset_token(token)

    try:
        validate_password(new_password, user=user)
    except ValidationError as exc:
        raise ValidationError(exc.messages) from exc

    user.set_password(new_password)
    user.save(update_fields=["password", "updated_at"])
    return user
