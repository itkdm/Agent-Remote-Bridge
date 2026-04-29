from __future__ import annotations

from pathlib import Path

from agent_remote_bridge.models import HostConfig
from agent_remote_bridge.services.audit_service import AuditService
from agent_remote_bridge.services.host_service import HostService
from agent_remote_bridge.stores.audit_store import AuditStore


class _FakeAdapter:
    def execute(self, host: HostConfig, remote_command: str, timeout_sec: int = 60):  # noqa: ANN001
        raise AssertionError("execute should not be called in this test")


def test_preflight_uses_auth_error_type_from_failed_connection_result(tmp_path: Path, monkeypatch) -> None:
    service = HostService(
        adapter=_FakeAdapter(),
        audit_service=AuditService(AuditStore(tmp_path / "audit.db")),
    )
    host = HostConfig(
        host_id="demo",
        host="127.0.0.1",
        username="root",
        auth_mode="password",
        password="secret",
        default_workdir="/root",
        allowed_paths=["/root"],
    )
    monkeypatch.setattr(
        "agent_remote_bridge.services.host_service.socket.getaddrinfo",
        lambda *args, **kwargs: [(None, None, None, None, ("127.0.0.1", 22))],
    )

    class _FakeSocket:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def settimeout(self, timeout: int) -> None:
            return None

        def recv(self, size: int) -> bytes:
            return b"SSH-2.0-OpenSSH_9.0"

    monkeypatch.setattr(
        "agent_remote_bridge.services.host_service.socket.create_connection",
        lambda *args, **kwargs: _FakeSocket(),
    )
    monkeypatch.setattr(
        service,
        "test_connection",
        lambda host, timeout_sec=15: {
            "ok": False,
            "summary": "SSH authentication failed",
            "error_type": "ssh_auth_failed",
        },
    )

    result = service.preflight(host, timeout_sec=5)

    assert result["ok"] is False
    assert result["stages"][-1]["name"] == "auth"
    assert result["stages"][-1]["error_type"] == "ssh_auth_failed"
