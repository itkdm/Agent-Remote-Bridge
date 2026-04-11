from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


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
    summary: str
    error_type: str | None = None
