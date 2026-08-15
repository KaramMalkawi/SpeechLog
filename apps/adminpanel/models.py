from __future__ import annotations

from django.conf import settings
from django.db import models


class AdminAuditLog(models.Model):
    """Immutable audit trail for admin dashboard actions."""

    class Action(models.TextChoices):
        ADMIN_LOGIN = "admin.login", "Admin login"
        CITY_FOUNDER_CREATE = "city_founder.create", "Create city founder"
        CITY_FOUNDER_UPDATE = "city_founder.update", "Update city founder"
        CITY_FOUNDER_DELETE = "city_founder.delete", "Delete city founder"
        ADMIN_CREATE = "admin.create", "Create admin"
        ADMIN_UPDATE = "admin.update", "Update admin"
        ADMIN_DELETE = "admin.delete", "Delete admin"
        USER_DELETE = "user.delete", "Delete user"
        USER_ROLE_UPDATE = "user.role_update", "Update user role"
        PASSWORD_CHANGE = "admin.password_change", "Change password"
        PROFILE_UPDATE = "admin.profile_update", "Update profile"
        GATHERING_DELETION_APPROVE = (
            "gathering.deletion_approve",
            "Approve gathering deletion",
        )
        GATHERING_DELETION_REJECT = (
            "gathering.deletion_reject",
            "Reject gathering deletion",
        )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admin_audit_logs",
    )
    action = models.CharField(max_length=64, choices=Action.choices, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["actor", "created_at"]),
            models.Index(fields=["action", "created_at"]),
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Admin audit logs are immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Admin audit logs are immutable.")
