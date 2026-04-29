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
        duration_ms: int | None = None,
        retry_count: int = 0,
        retried: bool = False,
        stderr_preview: str | None = None,
        error_type: str | None = None,
        failure_stage: str | None = None,
        suggested_next_actions: list[str] | None = None,
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
                duration_ms=duration_ms,
                retry_count=retry_count,
                retried=retried,
                stderr_preview=stderr_preview,
                summary=summary,
                error_type=error_type,
                failure_stage=failure_stage,
                suggested_next_actions=suggested_next_actions or [],
            )
        )

    def list_recent(
        self,
        *,
        limit: int = 20,
        host_id: str | None = None,
        session_id: str | None = None,
        tool_name: str | None = None,
        only_failures: bool = False,
    ) -> list[dict]:
        records = self._store.list_recent(
            limit=limit,
            host_id=host_id,
            session_id=session_id,
            tool_name=tool_name,
            only_failures=only_failures,
        )
        return [record.model_dump(mode="json") for record in records]
