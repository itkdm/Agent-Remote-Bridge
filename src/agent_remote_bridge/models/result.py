from __future__ import annotations

from pydantic import BaseModel, Field


class CommandResult(BaseModel):
    ok: bool
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    duration_ms: int
    cwd_after: str
    truncated: bool = False
    summary: str
    error_type: str | None = None
    risk_level: str = "low"
    risk_flags: list[str] = Field(default_factory=list)
    state_delta: dict = Field(default_factory=dict)
    suggested_next_actions: list[str] = Field(default_factory=list)


class ResponseEnvelope(BaseModel):
    ok: bool
    message: str
    data: dict | list | None = None
    warnings: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    truncated: bool = False
    error_type: str | None = None
