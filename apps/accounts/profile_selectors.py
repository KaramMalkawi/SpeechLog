from __future__ import annotations

from uuid import UUID

from django.db.models import Count, Exists, OuterRef

from apps.accounts.models import User, UserFollow
from core.storage import build_media_url


def get_membership_status(user: User) -> str:
    if user.role == User.Role.MEMBER and user.is_paid_member:
        return "active"
    return "inactive"


def get_membership_display_id(*, user: User) -> str:
    """Stable public membership label for the QR card (e.g. #13555)."""
    number = (user.id.int % 90_000) + 10_000
    return f"#{number}"


def get_membership_display_name(*, user: User) -> str:
    """Prefer OCR official name when present; otherwise profile display name."""
    official = (user.official_full_name or "").strip()
    if official:
        return official
    return (user.full_name or "").strip()


def get_profile_photo_url(user: User) -> str:
    return build_media_url(user.profile_photo_key)


def get_own_profile(user: User) -> User:
    return (
        User.objects.filter(pk=user.pk)
        .annotate(
            followers_count=Count("follower_relations", distinct=True),
            following_count=Count("following_relations", distinct=True),
        )
        .get()
    )


def is_following(*, follower_id: UUID, following_id: UUID) -> bool:
    if follower_id == following_id:
        return False
    return UserFollow.objects.filter(follower_id=follower_id, following_id=following_id).exists()


def get_public_profile(*, user_id: UUID, viewer: User | None = None) -> User | None:
    queryset = User.objects.filter(pk=user_id, is_active=True).annotate(
        followers_count=Count("follower_relations", distinct=True),
        following_count=Count("following_relations", distinct=True),
    )
    if viewer is not None:
        queryset = queryset.annotate(
            is_following=Exists(
                UserFollow.objects.filter(
                    follower_id=viewer.pk,
                    following_id=OuterRef("pk"),
                )
            )
        )

    profile = queryset.first()
    if profile is None:
        return None
    if viewer is None or viewer.pk != profile.pk:
        if not profile.is_identity_verified:
            return None
    return profile
