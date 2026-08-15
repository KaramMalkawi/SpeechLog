from __future__ import annotations

import pytest
from django.contrib.auth.models import Group, Permission

from apps.accounts.models import User
from apps.accounts.services import apply_user_role, clear_django_access_for_non_superusers
from tests.factories import UserFactory


@pytest.mark.django_db
def test_apply_user_role_clears_staff_and_django_perms_for_non_superuser():
    user = UserFactory(admin=True, is_staff=True, email="role-sync@example.com")
    permission = Permission.objects.first()
    assert permission is not None
    group = Group.objects.create(name="legacy-staff")
    user.groups.add(group)
    user.user_permissions.add(permission)

    apply_user_role(user, User.Role.CITY_FOUNDER)

    user.refresh_from_db()
    assert user.role == User.Role.CITY_FOUNDER
    assert user.is_staff is False
    assert user.is_superuser is False
    assert user.is_superadmin is False
    assert user.groups.count() == 0
    assert user.user_permissions.count() == 0


@pytest.mark.django_db
def test_apply_user_role_keeps_superadmin_staff_flags():
    user = UserFactory(
        admin=True,
        is_staff=True,
        is_superuser=True,
        email="superadmin@example.com",
    )

    apply_user_role(user, User.Role.ADMIN)

    user.refresh_from_db()
    assert user.role == User.Role.ADMIN
    assert user.is_staff is True
    assert user.is_superuser is True
    assert user.is_superadmin is True


@pytest.mark.django_db
def test_apply_user_role_rejects_invalid_role():
    user = UserFactory(email="bad-role@example.com")
    with pytest.raises(ValueError, match="Invalid role"):
        apply_user_role(user, "not_a_role")


@pytest.mark.django_db
def test_clear_django_access_for_non_superusers():
    staff_admin = UserFactory(admin=True, is_staff=True, email="staff-admin@example.com")
    permission = Permission.objects.first()
    assert permission is not None
    staff_admin.user_permissions.add(permission)

    superuser = UserFactory(
        admin=True,
        is_staff=True,
        is_superuser=True,
        email="keep-super@example.com",
    )

    clear_django_access_for_non_superusers()

    staff_admin.refresh_from_db()
    superuser.refresh_from_db()
    assert staff_admin.is_staff is False
    assert staff_admin.user_permissions.count() == 0
    assert superuser.is_staff is True
    assert superuser.is_superuser is True
