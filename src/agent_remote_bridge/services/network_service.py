from __future__ import annotations

from agent_remote_bridge.adapters.ssh_adapter import SSHAdapter
from agent_remote_bridge.models import HostConfig, SessionState
from agent_remote_bridge.services.audit_service import AuditService
from agent_remote_bridge.utils.suggested_actions import suggested_actions_for_error
from agent_remote_bridge.utils.truncation import truncate_text


class NetworkService:
    def __init__(self, *, adapter: SSHAdapter, audit_service: AuditService) -> None:
        self._adapter = adapter
        self._audit_service = audit_service

    def check_port_listening(
        self,
        *,
        host: HostConfig,
        session: SessionState,
        port: int,
    ) -> dict:
        commands = [
            ("ss", f"ss -lntp '( sport = :{int(port)} )'"),
            ("netstat", f"netstat -lntp 2>/dev/null | grep ':{int(port)} '"),
        ]
        errors: list[str] = []
        for backend, command in commands:
            result = self._adapter.execute(host, command)
            stdout, stdout_truncated = truncate_text(result.stdout)
            stderr, stderr_truncated = truncate_text(result.stderr, max_chars=2000)
            lines = [line for line in stdout.splitlines() if line.strip()]
            data_lines = lines[1:] if backend == "ss" and lines else lines
            text = "\n".join(data_lines).strip()
            if result.exit_code == 0 and text:
                summary = f"Port {port} is listening via {backend}"
                self._audit_service.record(
                    host_id=host.host_id,
                    session_id=session.session_id,
                    tool_name="check_port_listening",
                    command=command,
                    exit_code=result.exit_code,
                    summary=summary,
                )
                return {
                    "ok": True,
                    "port": port,
                    "is_listening": True,
                    "backend": backend,
                    "content": text,
                    "stderr": stderr,
                    "summary": summary,
                    "exit_code": result.exit_code,
                    "truncated": stdout_truncated or stderr_truncated,
                    "error_type": None,
                    "suggested_next_actions": [],
                }
            if stderr.strip():
                errors.append(f"{backend}: {stderr.strip().splitlines()[0][:160]}")

        summary = f"Port {port} is not listening"
        self._audit_service.record(
            host_id=host.host_id,
            session_id=session.session_id,
            tool_name="check_port_listening",
            command=str(port),
            exit_code=0,
            summary=summary,
            error_type=None,
        )
        return {
            "ok": True,
            "port": port,
            "is_listening": False,
            "backend": None,
            "content": "",
            "stderr": "\n".join(errors),
            "summary": summary,
            "exit_code": 0,
            "truncated": False,
            "error_type": None,
            "suggested_next_actions": ["check whether the service is expected to be running", "verify the configured port number"],
        }
