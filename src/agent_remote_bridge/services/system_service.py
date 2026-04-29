from __future__ import annotations

from agent_remote_bridge.adapters.ssh_adapter import SSHAdapter
from agent_remote_bridge.models import HostConfig, SessionState
from agent_remote_bridge.services.audit_service import AuditService
from agent_remote_bridge.utils.suggested_actions import suggested_actions_for_error
from agent_remote_bridge.utils.truncation import truncate_text


class SystemService:
    def __init__(self, *, adapter: SSHAdapter, audit_service: AuditService) -> None:
        self._adapter = adapter
        self._audit_service = audit_service

    def check_service_status(
        self,
        *,
        host: HostConfig,
        session: SessionState,
        service_name: str,
    ) -> dict:
        commands = [
            ("systemd", f"systemctl status {service_name} --no-pager"),
            ("service", f"service {service_name} status"),
        ]
        errors: list[str] = []
        for backend, command in commands:
            result = self._adapter.execute(host, command)
            stdout, stdout_truncated = truncate_text(result.stdout)
            stderr, stderr_truncated = truncate_text(result.stderr, max_chars=2000)
            text = stdout or stderr
            if result.exit_code == 0 or text.strip():
                lowered = text.lower()
                if "active (running)" in lowered or "is running" in lowered:
                    status = "running"
                    ok = True
                    error_type = None
                    suggested_next_actions: list[str] = []
                elif "inactive" in lowered:
                    status = "inactive"
                    ok = True
                    error_type = None
                    suggested_next_actions = ["inspect recent service logs", "review the service configuration or startup conditions"]
                elif "failed" in lowered:
                    status = "failed"
                    ok = True
                    error_type = None
                    suggested_next_actions = ["inspect recent service logs", "check the last restart failure details"]
                elif "not-found" in lowered or "could not be found" in lowered:
                    status = "not_found"
                    ok = True
                    error_type = None
                    suggested_next_actions = ["check the service name", "confirm the service is installed on the remote host"]
                else:
                    status = "unknown"
                    ok = result.exit_code == 0
                    error_type = None if ok else "unsupported_remote_state"
                    suggested_next_actions = [] if ok else suggested_actions_for_error("unsupported_remote_state")
                summary = f"Service {service_name} status via {backend}: {status}"
                self._audit_service.record(
                    host_id=host.host_id,
                    session_id=session.session_id,
                    tool_name="check_service_status",
                    command=command,
                    exit_code=result.exit_code,
                    summary=summary,
                    error_type=error_type,
                )
                return {
                    "ok": ok,
                    "service_name": service_name,
                    "backend": backend,
                    "status": status,
                    "content": stdout,
                    "stderr": stderr,
                    "summary": summary,
                    "exit_code": result.exit_code,
                    "truncated": stdout_truncated or stderr_truncated,
                    "error_type": error_type,
                    "suggested_next_actions": suggested_next_actions,
                }
            if stderr.strip():
                errors.append(f"{backend}: {stderr.strip().splitlines()[0][:160]}")

        summary = f"Unable to determine status for service {service_name}"
        if errors:
            summary = f"{summary}: {'; '.join(errors)}"
        self._audit_service.record(
            host_id=host.host_id,
            session_id=session.session_id,
            tool_name="check_service_status",
            command=service_name,
            exit_code=1,
            summary=summary,
            error_type="remote_execution_failed",
        )
        return {
            "ok": False,
            "service_name": service_name,
            "backend": None,
            "status": "unknown",
            "content": "",
            "stderr": "\n".join(errors),
            "summary": summary,
            "exit_code": 1,
            "truncated": False,
            "error_type": "remote_execution_failed",
            "suggested_next_actions": suggested_actions_for_error("remote_execution_failed"),
        }
