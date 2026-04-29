from __future__ import annotations

import subprocess

import pytest

from agent_remote_bridge.adapters.ssh_adapter import SSHAdapter
from agent_remote_bridge.models import HostConfig
from agent_remote_bridge.utils.errors import SSHAuthError, SSHBannerError, SSHConnectionError


def _key_path_host() -> HostConfig:
    return HostConfig(
        host_id="demo",
        host="example.com",
        username="deploy",
        auth_mode="key_path",
        private_key_path="C:/keys/id_rsa",
        default_workdir="/srv/app",
        allowed_paths=["/srv/app"],
    )


def test_execute_classifies_system_ssh_auth_failure(monkeypatch) -> None:
    adapter = SSHAdapter()
    host = _key_path_host()
    monkeypatch.setattr(
        "agent_remote_bridge.adapters.ssh_adapter.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0],
            255,
            stdout="",
            stderr="deploy@example.com: Permission denied (publickey).",
        ),
    )

    with pytest.raises(SSHAuthError):
        adapter.execute(host, "pwd", timeout_sec=5)


def test_execute_classifies_system_ssh_connection_failure(monkeypatch) -> None:
    adapter = SSHAdapter()
    host = _key_path_host()
    monkeypatch.setattr(
        "agent_remote_bridge.adapters.ssh_adapter.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0],
            255,
            stdout="",
            stderr="ssh: connect to host example.com port 22: Connection refused",
        ),
    )

    with pytest.raises(SSHConnectionError):
        adapter.execute(host, "pwd", timeout_sec=5)


def test_classify_paramiko_no_existing_session_as_banner_error() -> None:
    adapter = SSHAdapter()

    error = adapter._classify_paramiko_error(Exception("No existing session"))

    assert isinstance(error, SSHBannerError)
