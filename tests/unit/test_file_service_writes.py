from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from agent_remote_bridge.adapters.base import ExecutionResult
from agent_remote_bridge.models import HostConfig, SessionState
from agent_remote_bridge.services.audit_service import AuditService
from agent_remote_bridge.services.file_service import FileService
from agent_remote_bridge.services.security_guard import SecurityGuard
from agent_remote_bridge.stores.audit_store import AuditStore
from agent_remote_bridge.utils.errors import SecurityError


class _FakeAdapter:
    def __init__(self, *, exit_code: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.commands: list[str] = []

    def execute(self, host: HostConfig, remote_command: str, timeout_sec: int = 60) -> ExecutionResult:  # noqa: ANN001
        self.commands.append(remote_command)
        return ExecutionResult(
            exit_code=self.exit_code,
            stdout=self.stdout,
            stderr=self.stderr,
            duration_ms=12,
        )


def _host() -> HostConfig:
    return HostConfig(
        host_id="demo",
        host="127.0.0.1",
        username="root",
        auth_mode="password",
        password="secret",
        default_workdir="/root",
        allowed_paths=["/root", "/srv/app"],
        allow_sudo=True,
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


def _service(tmp_path: Path, adapter: _FakeAdapter) -> tuple[FileService, AuditService]:
    audit_service = AuditService(AuditStore(tmp_path / "audit.db"))
    return (
        FileService(
            adapter=adapter,
            security_guard=SecurityGuard(),
            audit_service=audit_service,
        ),
        audit_service,
    )


def test_write_file_overwrites_allowed_path_and_records_audit(tmp_path: Path) -> None:
    adapter = _FakeAdapter()
    service, audit_service = _service(tmp_path, adapter)

    result = service.write_file(
        host=_host(),
        session=_session(),
        path="/srv/app/.env",
        content="APP_ENV=prod\n",
    )

    assert result["ok"] is True
    assert result["mode"] == "write"
    assert "mktemp" in adapter.commands[0]
    assert "mv " in adapter.commands[0]
    assert "__ARB_EOF__" not in adapter.commands[0]
    record = audit_service.list_recent(limit=1)[0]
    assert record["tool_name"] == "write_remote_file"


def test_append_file_uses_append_redirection(tmp_path: Path) -> None:
    adapter = _FakeAdapter()
    service, _ = _service(tmp_path, adapter)

    result = service.append_file(
        host=_host(),
        session=_session(),
        path="/srv/app/.env",
        content="DEBUG=1\n",
    )

    assert result["ok"] is True
    assert result["mode"] == "append"
    assert ">> /srv/app/.env" in adapter.commands[0]
    assert "__ARB_EOF__" not in adapter.commands[0]


def test_write_file_supports_content_containing_previous_delimiter_token(tmp_path: Path) -> None:
    adapter = _FakeAdapter()
    service, _ = _service(tmp_path, adapter)

    result = service.write_file(
        host=_host(),
        session=_session(),
        path="/srv/app/.env",
        content="FIRST=1\n__ARB_EOF__\nSECOND=2\n",
    )

    assert result["ok"] is True
    assert "__ARB_WRITE_" in adapter.commands[0]
    assert "cat <<'__ARB_EOF__'" not in adapter.commands[0]


def test_write_file_rejects_paths_outside_allowed_roots(tmp_path: Path) -> None:
    adapter = _FakeAdapter()
    service, _ = _service(tmp_path, adapter)

    with pytest.raises(SecurityError):
        service.write_file(
            host=_host(),
            session=_session(),
            path="/etc/nginx/nginx.conf",
            content="worker_processes 1;\n",
        )


def test_write_file_rejects_large_payloads(tmp_path: Path) -> None:
    adapter = _FakeAdapter()
    service, _ = _service(tmp_path, adapter)

    result = service.write_file(
        host=_host(),
        session=_session(),
        path="/srv/app/large.txt",
        content="x" * 20001,
    )

    assert result["ok"] is False
    assert result["error_type"] == "command_blocked"
    assert result["summary"] == "Write payload exceeds the maximum allowed size"
