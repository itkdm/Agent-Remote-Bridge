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
    assert "critical_command" in result.risk_flags
    assert "destructive_command" in result.risk_flags


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
    assert "service_control_command" in result.risk_flags
    assert "approval_required" in result.risk_flags


def test_check_command_allows_high_risk_command_after_explicit_approval() -> None:
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

    result = guard.check_command(host=host, command="chmod -R 755 /srv/app", require_approval=True)

    assert result.allowed is True
    assert result.risk_level == "high"
    assert "permission_change_command" in result.risk_flags


def test_check_command_marks_network_risk_category() -> None:
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

    result = guard.check_command(host=host, command="iptables -L", require_approval=True)

    assert result.allowed is False
    assert result.risk_level == "critical"
    assert "network_command" in result.risk_flags


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
