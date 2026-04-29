from __future__ import annotations

from agent_remote_bridge.models import HostConfig
from agent_remote_bridge.services.security_guard import SecurityGuard


def test_check_command_blocks_critical_command() -> None:
    guard = SecurityGuard()
    host = HostConfig(
        host_id="demo",
        host="127.0.0.1",
        username="root",
        auth_mode="password",
        password="secret",
        default_workdir="/root",
        allowed_paths=["/root"],
    )

    result = guard.check_command(host=host, command="rm -rf /tmp && rm -rf /", require_approval=True)

    assert result.allowed is False
    assert result.risk_level == "critical"
    assert result.risk_flags == ["critical_command"]


def test_check_command_requires_approval_for_high_risk() -> None:
    guard = SecurityGuard()
    host = HostConfig(
        host_id="demo",
        host="127.0.0.1",
        username="root",
        auth_mode="password",
        password="secret",
        default_workdir="/root",
        allowed_paths=["/root"],
    )

    result = guard.check_command(host=host, command="systemctl stop nginx", require_approval=False)

    assert result.allowed is False
    assert result.risk_level == "high"
    assert result.risk_flags == ["high_risk_command", "approval_required"]


def test_check_path_rejects_paths_outside_allowed_roots() -> None:
    guard = SecurityGuard()
    host = HostConfig(
        host_id="demo",
        host="127.0.0.1",
        username="root",
        auth_mode="password",
        password="secret",
        default_workdir="/root",
        allowed_paths=["/srv/app"],
    )

    result = guard.check_path(host=host, path="/etc/nginx/nginx.conf")

    assert result.allowed is False
    assert result.risk_flags == ["path_not_allowed"]
