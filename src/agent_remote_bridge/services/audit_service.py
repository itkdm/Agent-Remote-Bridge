from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from agent_remote_bridge.models import AuditRecord
from agent_remote_bridge.stores.audit_store import AuditStore


class AuditService:
    def __init__(self, store: AuditStore) -> None:
        self._store = store

    def record(
        self,
        *,
        host_id: str,
        tool_name: str,
        summary: str,
        session_id: str | None = None,
        command: str | None = None,
        risk_level: str = "low",
        blocked: bool = False,
        exit_code: int | None = None,
        error_type: str | None = None,
    ) -> None:
        self._store.write(
            AuditRecord(
                audit_id=f"aud_{uuid4().hex[:12]}",
                timestamp=datetime.now().astimezone(),
                host_id=host_id,
                session_id=session_id,
                tool_name=tool_name,
                command=command,
                risk_level=risk_level,
                blocked=blocked,
                exit_code=exit_code,
                summary=summary,
                error_type=error_type,
            )
        )
