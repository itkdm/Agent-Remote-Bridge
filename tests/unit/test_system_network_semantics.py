from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from agent_remote_bridge.adapters.base import ExecutionResult
from agent_remote_bridge.models import HostConfig, SessionState
from agent_remote_bridge.services.audit_service import AuditService
from agent_remote_bridge.services.network_service import NetworkService
from agent_remote_bridge.services.system_service import SystemService
from agent_remote_bridge.stores.audit_store import AuditStore


class _SequenceAdapter:
    def __init__(self, results: list[ExecutionResult]) -> None:
        self._results = list(results)

    def execute(self, host: HostConfig, remote_command: str, timeout_sec: int = 60) -> ExecutionResult:  # noqa: ANN001
        assert self._results, "no more fake results configured"
        return self._results.pop(0)


def _host() -> HostConfig:
    return HostConfig(
        host_id="demo",
        host="127.0.0.1",
        username="root",
        auth_mode="password",
        password="secret",
        default_workdir="/root",
        allowed_paths=["/root", "/var/log"],
    )


def _session() -> SessionState:
    now = datetime.now(timezone.utc)
    return SessionState(
        session_id="sess_demo",
        host_id="demo",
        current_cwd="/root",
        created_at=now,
        updated_at=now,
    )


def test_check_service_status_reports_inactive_without_execution_error(tmp_path: Path) -> None:
    adapter = _SequenceAdapter(
        [
            ExecutionResult(
                exit_code=3,
                stdout="Active: inactive (dead)",
                stderr="",
                duration_ms=10,
            )
        ]
    )
    service = SystemService(
        adapter=adapter,
        audit_service=AuditService(AuditStore(tmp_path / "audit.db")),
    )

    result = service.check_service_status(host=_host(), session=_session(), service_name="nginx")

    assert result["ok"] is True
    assert result["status"] == "inactive"
    assert result["error_type"] is None
    assert result["suggested_next_actions"]


def test_check_port_listening_reports_not_listening_without_execution_error(tmp_path: Path) -> None:
    adapter = _SequenceAdapter(
        [
            ExecutionResult(exit_code=1, stdout="", stderr="", duration_ms=10),
            ExecutionResult(exit_code=1, stdout="", stderr="", duration_ms=10),
        ]
    )
    service = NetworkService(
        adapter=adapter,
        audit_service=AuditService(AuditStore(tmp_path / "audit.db")),
    )

    result = service.check_port_listening(host=_host(), session=_session(), port=8080)

    assert result["ok"] is True
    assert result["is_listening"] is False
    assert result["error_type"] is None
    assert result["summary"] == "Port 8080 is not listening"
