from __future__ import annotations

from pydantic import BaseModel, Field


class SecurityPolicy(BaseModel):
    policy_id: str = "default-safe"
    blocked_patterns: list[str] = Field(
        default_factory=lambda: ["rm -rf /", "mkfs", "iptables", "shutdown ", "reboot "]
    )
    high_risk_patterns: list[str] = Field(
        default_factory=lambda: [
            "systemctl stop",
            "chmod -R",
            "chown -R",
            "rm -rf",
            "mv /etc/",
            "cp /etc/",
        ]
    )
    deny_critical: bool = True
    require_approval_for_high_risk: bool = True


class SecurityCheckResult(BaseModel):
    allowed: bool
    risk_level: str
    risk_flags: list[str] = Field(default_factory=list)
    message: str | None = None
