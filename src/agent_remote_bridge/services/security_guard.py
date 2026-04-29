from __future__ import annotations

import re
from pathlib import PurePosixPath

from agent_remote_bridge.models import HostConfig, SecurityCheckResult, SecurityPolicy


class SecurityGuard:
    _CATEGORY_RULES = (
        {
            "flag": "destructive_command",
            "risk_level": "critical",
            "patterns": (
                r"\brm\s+-rf\s+/",
                r"\bmkfs(\.[a-z0-9]+)?\b",
                r"\bdd\s+if=",
            ),
        },
        {
            "flag": "network_command",
            "risk_level": "critical",
            "patterns": (
                r"\biptables\b",
                r"\bufw\b",
                r"\bfirewall-cmd\b",
            ),
        },
        {
            "flag": "service_control_command",
            "risk_level": "high",
            "patterns": (
                r"\bsystemctl\s+(stop|restart|reload)\b",
                r"\bservice\s+\S+\s+(stop|restart|reload)\b",
            ),
        },
        {
            "flag": "permission_change_command",
            "risk_level": "high",
            "patterns": (
                r"\bchmod\s+-r\b",
                r"\bchown\s+-r\b",
            ),
        },
        {
            "flag": "file_write_command",
            "risk_level": "high",
            "patterns": (
                r">\s*/etc/",
                r">>\s*/etc/",
                r"\btee\s+/etc/",
                r"\bcp\s+/etc/",
                r"\bmv\s+/etc/",
            ),
        },
    )
    _RISK_ORDER = {"low": 0, "high": 1, "critical": 2}

    def __init__(self, policy: SecurityPolicy | None = None) -> None:
        self._policy = policy or SecurityPolicy()

    def check_command(
        self,
        *,
        host: HostConfig,
        command: str,
        use_sudo: bool = False,
        require_approval: bool = False,
    ) -> SecurityCheckResult:
        normalized = command.strip().lower()
        risk_level = "low"
        risk_flags: list[str] = []

        for rule in self._CATEGORY_RULES:
            if any(re.search(pattern, normalized) for pattern in rule["patterns"]):
                risk_flags.append(rule["flag"])
                if self._RISK_ORDER[rule["risk_level"]] > self._RISK_ORDER[risk_level]:
                    risk_level = rule["risk_level"]

        for pattern in self._policy.blocked_patterns:
            if pattern.lower() in normalized:
                if "critical_command" not in risk_flags:
                    risk_flags.append("critical_command")
                return SecurityCheckResult(
                    allowed=False,
                    risk_level="critical",
                    risk_flags=risk_flags,
                    message=f"Command blocked by policy pattern: {pattern}",
                )

        for pattern in self._policy.high_risk_patterns:
            if pattern.lower() in normalized:
                if self._RISK_ORDER["high"] > self._RISK_ORDER[risk_level]:
                    risk_level = "high"
                if "high_risk_command" not in risk_flags:
                    risk_flags.append("high_risk_command")
                break

        if use_sudo:
            risk_flags.append("sudo_command")
            if not host.allow_sudo:
                return SecurityCheckResult(
                    allowed=False,
                    risk_level="high",
                    risk_flags=risk_flags + ["sudo_not_allowed"],
                    message="sudo is not allowed for this host",
                )
            risk_level = "high"

        if risk_level == "high" and self._policy.require_approval_for_high_risk and not require_approval:
            return SecurityCheckResult(
                allowed=False,
                risk_level=risk_level,
                risk_flags=risk_flags + ["approval_required"],
                message="High risk command requires explicit approval",
            )

        return SecurityCheckResult(allowed=True, risk_level=risk_level, risk_flags=risk_flags)

    def check_path(self, *, host: HostConfig, path: str) -> SecurityCheckResult:
        if not host.allowed_paths:
            return SecurityCheckResult(allowed=True, risk_level="low")

        candidate = PurePosixPath(path)
        for allowed in host.allowed_paths:
            allowed_path = PurePosixPath(allowed)
            if candidate == allowed_path or allowed_path in candidate.parents:
                return SecurityCheckResult(allowed=True, risk_level="low")

        return SecurityCheckResult(
            allowed=False,
            risk_level="high",
            risk_flags=["path_not_allowed"],
            message=f"Path '{path}' is outside allowed paths",
        )
