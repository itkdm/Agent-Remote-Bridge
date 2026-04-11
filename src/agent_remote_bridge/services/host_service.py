from __future__ import annotations

from agent_remote_bridge.adapters.ssh_adapter import SSHAdapter
from agent_remote_bridge.models import HostConfig
from agent_remote_bridge.services.audit_service import AuditService
from agent_remote_bridge.utils.truncation import truncate_text


class HostService:
    def __init__(self, *, adapter: SSHAdapter, audit_service: AuditService) -> None:
        self._adapter = adapter
        self._audit_service = audit_service

    def test_connection(self, host: HostConfig, timeout_sec: int = 15) -> dict:
        result = self._adapter.execute(host, "printf 'ok'", timeout_sec=timeout_sec)
        stdout, truncated = truncate_text(result.stdout, max_chars=200)
        stderr, _ = truncate_text(result.stderr, max_chars=400)
        ok = result.exit_code == 0 and stdout.strip() == "ok"
        summary = "SSH connection succeeded" if ok else "SSH connection failed"
        self._audit_service.record(
            host_id=host.host_id,
            tool_name="test_host_connection",
            command="printf 'ok'",
            exit_code=result.exit_code,
            summary=summary,
            error_type=None if ok else "remote_execution_failed",
        )
        return {
            "host_id": host.host_id,
            "ok": ok,
            "exit_code": result.exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "duration_ms": result.duration_ms,
            "summary": summary,
            "truncated": truncated,
        }
