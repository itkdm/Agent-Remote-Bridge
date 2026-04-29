from __future__ import annotations

from pathlib import Path

from agent_remote_bridge.stores.host_store import HostStore


def test_validate_config_requires_existing_password_env(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "hosts.yaml"
    config_path.write_text(
        """
hosts:
  - host_id: demo
    host: 127.0.0.1
    port: 22
    username: root
    auth_mode: password
    password_env: ARB_DEMO_PASSWORD
    default_workdir: /root
    allowed_paths:
      - /root
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.delenv("ARB_DEMO_PASSWORD", raising=False)

    validation = HostStore(config_path).validate_config()

    assert validation["ok"] is False
    assert "demo: password_env is set but environment variable is missing: ARB_DEMO_PASSWORD" in validation["errors"]


def test_validate_config_reports_valid_password_host(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "hosts.yaml"
    config_path.write_text(
        """
hosts:
  - host_id: demo
    alias: demo
    host: 127.0.0.1
    port: 22
    username: root
    auth_mode: password
    password_env: ARB_DEMO_PASSWORD
    default_workdir: /root
    allowed_paths:
      - /root
    allow_sudo: true
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("ARB_DEMO_PASSWORD", "secret")

    validation = HostStore(config_path).validate_config()

    assert validation["ok"] is True
    assert validation["errors"] == []
    assert validation["host_count"] == 1
    assert validation["hosts"][0]["host_id"] == "demo"
    assert validation["hosts"][0]["ok"] is True
