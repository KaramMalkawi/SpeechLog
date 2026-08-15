from __future__ import annotations

from django.db.models import Q, QuerySet

from apps.accounts.models import User
from apps.adminpanel.models import AdminAuditLog


def admin_audit_log_queryset() -> QuerySet[AdminAuditLog]:
    return AdminAuditLog.objects.select_related("actor").all()


def list_admin_audit_logs(
    *,
    actor_role: str | None = None,
    action: str | None = None,
    search: str | None = None,
    limit: int = 200,
) -> list[AdminAuditLog]:
    """Return recent admin/superadmin audit events, newest first."""
    qs = admin_audit_log_queryset().order_by("-created_at", "-id")

    # Audit trail is for dashboard operators — restrict to admin role or superusers.
    qs = qs.filter(Q(actor__is_superuser=True) | Q(actor__role=User.Role.ADMIN))

    if actor_role == "superadmin":
        qs = qs.filter(actor__is_superuser=True)
    elif actor_role == "admin":
        qs = qs.filter(actor__is_superuser=False, actor__role=User.Role.ADMIN)

    if action:
        qs = qs.filter(action=action)

    if search:
        term = search.strip()
        if term:
            qs = qs.filter(
                Q(actor__email__icontains=term)
                | Q(actor__full_name__icontains=term)
                | Q(action__icontains=term)
                | Q(metadata__icontains=term)
            )

    try:
        parsed_limit = int(limit)
    except (TypeError, ValueError):
        parsed_limit = 200
    parsed_limit = max(1, min(parsed_limit, 500))
    return list(qs[:parsed_limit])
