from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SessionState(BaseModel):
    session_id: str
    host_id: str
    status: str = "open"
    current_cwd: str
    env_delta: dict[str, str] = Field(default_factory=dict)
    detected_os: str | None = None
    privilege_level: str = "user"
    recent_commands: list[str] = Field(default_factory=list)
    recent_failures: list[str] = Field(default_factory=list)
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None = None
