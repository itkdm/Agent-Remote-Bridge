from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AuditRecord(BaseModel):
    audit_id: str
    timestamp: datetime
    host_id: str
    session_id: str | None = None
    tool_name: str
    command: str | None = None
    risk_level: str = "low"
    blocked: bool = False
    exit_code: int | None = None
    duration_ms: int | None = None
    retry_count: int = 0
    retried: bool = False
    stderr_preview: str | None = None
    summary: str
    error_type: str | None = None
    suggested_next_actions: list[str] = Field(default_factory=list)
