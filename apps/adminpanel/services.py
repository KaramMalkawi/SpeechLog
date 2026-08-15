from __future__ import annotations

from uuid import UUID

from django.db import transaction

from apps.adminpanel.models import AdminAuditLog

ADMIN_LOGIN_ACTION = AdminAuditLog.Action.ADMIN_LOGIN
CITY_FOUNDER_CREATE_ACTION = AdminAuditLog.Action.CITY_FOUNDER_CREATE
CITY_FOUNDER_UPDATE_ACTION = AdminAuditLog.Action.CITY_FOUNDER_UPDATE
CITY_FOUNDER_DELETE_ACTION = AdminAuditLog.Action.CITY_FOUNDER_DELETE
ADMIN_CREATE_ACTION = AdminAuditLog.Action.ADMIN_CREATE
ADMIN_UPDATE_ACTION = AdminAuditLog.Action.ADMIN_UPDATE
ADMIN_DELETE_ACTION = AdminAuditLog.Action.ADMIN_DELETE
USER_DELETE_ACTION = AdminAuditLog.Action.USER_DELETE
USER_ROLE_UPDATE_ACTION = AdminAuditLog.Action.USER_ROLE_UPDATE
PASSWORD_CHANGE_ACTION = AdminAuditLog.Action.PASSWORD_CHANGE
PROFILE_UPDATE_ACTION = AdminAuditLog.Action.PROFILE_UPDATE


@transaction.atomic
def record_admin_audit_event(
    *,
    actor_id: UUID | str,
    action: str,
    metadata: dict | None = None,
) -> AdminAuditLog:
    return AdminAuditLog.objects.create(
        actor_id=actor_id,
        action=action,
        metadata=metadata or {},
    )


def _actor_role_label(*, is_superuser: bool, role: str) -> str:
    if is_superuser:
        return "Super Admin"
    if role == "admin":
        return "Admin"
    return role.replace("_", " ").title()


def _action_label(action: str) -> str:
    try:
        return AdminAuditLog.Action(action).label
    except ValueError:
        return action


def _summarize_metadata(action: str, metadata: dict) -> str:
    meta = metadata or {}
    if action == AdminAuditLog.Action.ADMIN_LOGIN:
        return meta.get("email") or "Dashboard login"
    if action in {
        AdminAuditLog.Action.CITY_FOUNDER_CREATE,
        AdminAuditLog.Action.CITY_FOUNDER_UPDATE,
        AdminAuditLog.Action.CITY_FOUNDER_DELETE,
    }:
        name = meta.get("full_name") or ""
        email = meta.get("email") or ""
        city = meta.get("city_name") or meta.get("city_id") or ""
        parts = [p for p in (name, email, f"city={city}" if city else "") if p]
        return " · ".join(parts) or "City founder"
    if action in {
        AdminAuditLog.Action.ADMIN_CREATE,
        AdminAuditLog.Action.ADMIN_UPDATE,
        AdminAuditLog.Action.ADMIN_DELETE,
    }:
        name = meta.get("full_name") or ""
        email = meta.get("email") or ""
        parts = [p for p in (name, email) if p]
        return " · ".join(parts) or "Admin"
    if action == AdminAuditLog.Action.USER_DELETE:
        return meta.get("email") or meta.get("full_name") or meta.get("user_id") or "User deleted"
    if action == AdminAuditLog.Action.USER_ROLE_UPDATE:
        email = meta.get("email") or meta.get("user_id") or "User"
        previous = meta.get("previous_role") or "?"
        new = meta.get("new_role") or "?"
        return f"{email}: {previous} → {new}"
    if action == AdminAuditLog.Action.PASSWORD_CHANGE:
        return "Password updated"
    if action == AdminAuditLog.Action.PROFILE_UPDATE:
        return meta.get("full_name") or "Profile updated"
    if not meta:
        return "—"
    # Fallback: compact key highlights
    preferred = ("email", "full_name", "user_id", "city_name", "detail")
    bits = [str(meta[k]) for k in preferred if meta.get(k)]
    return " · ".join(bits) if bits else "—"


def audit_log_to_payload(log: AdminAuditLog) -> dict:
    actor = log.actor
    if actor is None:
        return {
            "id": log.id,
            "created_at": log.created_at,
            "action": log.action,
            "action_label": _action_label(log.action),
            "actor_id": None,
            "actor_email": "",
            "actor_full_name": "Deleted user",
            "actor_role": "",
            "actor_role_label": "Deleted user",
            "summary": _summarize_metadata(log.action, log.metadata or {}),
            "metadata": log.metadata or {},
        }
    return {
        "id": log.id,
        "created_at": log.created_at,
        "action": log.action,
        "action_label": _action_label(log.action),
        "actor_id": actor.id,
        "actor_email": actor.email,
        "actor_full_name": actor.full_name or "",
        "actor_role": "superadmin" if actor.is_superuser else actor.role,
        "actor_role_label": _actor_role_label(
            is_superuser=actor.is_superuser,
            role=actor.role,
        ),
        "summary": _summarize_metadata(log.action, log.metadata or {}),
        "metadata": log.metadata or {},
    }
