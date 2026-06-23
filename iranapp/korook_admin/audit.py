"""Admin audit trail helpers."""

from __future__ import annotations

from typing import Any

from korook_platform.models import AdminAuditLog


def log_admin_action(
    *,
    actor,
    action_type: str,
    object_type: str,
    object_id: int,
    summary: str,
    before_state: dict[str, Any] | None = None,
    after_state: dict[str, Any] | None = None,
    admin_note: str = "",
) -> AdminAuditLog:
    return AdminAuditLog.objects.create(
        actor=actor,
        action_type=action_type,
        object_type=object_type,
        object_id=object_id,
        summary=summary[:500],
        before_state=before_state,
        after_state=after_state,
        admin_note=admin_note or "",
    )
