from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def write_audit_log(
    db: Session,
    *,
    actor_user_id: int | None,
    actor_role: str | None,
    event_type: str,
    target_type: str | None = None,
    target_id: str | None = None,
    severity: str = "info",
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        event_type=event_type,
        target_type=target_type,
        target_id=target_id,
        severity=severity,
        metadata_json=json.dumps(metadata or {}, ensure_ascii=True),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
