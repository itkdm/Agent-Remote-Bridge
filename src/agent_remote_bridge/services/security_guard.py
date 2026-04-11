from __future__ import annotations

from pathlib import PurePosixPath

from agent_remote_bridge.models import HostConfig, SecurityCheckResult, SecurityPolicy


class SecurityGuard:
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
        for pattern in self._policy.blocked_patterns:
            if pattern.lower() in normalized:
                return SecurityCheckResult(
                    allowed=False,
                    risk_level="critical",
                    risk_flags=["critical_command"],
                    message=f"Command blocked by policy pattern: {pattern}",
                )

        risk_level = "low"
        risk_flags: list[str] = []

        for pattern in self._policy.high_risk_patterns:
            if pattern.lower() in normalized:
                risk_level = "high"
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
