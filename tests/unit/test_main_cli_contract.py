from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from agent_remote_bridge import main


def test_status_command_emits_connection_error_payload(monkeypatch, capsys) -> None:
    monkeypatch.setattr(main, "_probe_tcp", lambda host, port: False)
    monkeypatch.setattr(
        main,
        "_read_codex_server_status",
        lambda server_name, url: {
            "registered": False,
            "config_path": "C:/Users/test/.codex/config.toml",
            "detail": "Server not found in Codex config",
        },
    )

    exit_code = main._status_command(
        Namespace(host="127.0.0.1", port=8000, codex_server_name="agentRemoteBridge")
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["error_type"] == "connection_error"
    assert payload["suggested_next_actions"]


def test_config_validate_command_emits_config_error_payload(tmp_path: Path, monkeypatch, capsys) -> None:
    missing_config = tmp_path / "missing-hosts.yaml"
    monkeypatch.setattr(
        main,
        "load_settings",
        lambda: type(
            "Settings",
            (),
            {
                "host_config_path": missing_config,
                "sqlite_path": tmp_path / "state.db",
            },
        )(),
    )

    exit_code = main._config_validate_command(
        Namespace(config_path=str(missing_config), sqlite_path=None, experimental_tools=False)
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["error_type"] == "config_error"
    assert payload["suggested_next_actions"]
