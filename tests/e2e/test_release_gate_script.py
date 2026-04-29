from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_release_gate_module():
    module_path = Path(__file__).resolve().parents[2] / "scripts" / "release_gate.py"
    spec = importlib.util.spec_from_file_location("arb_release_gate", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_build_check_commands_includes_local_release_gates() -> None:
    module = _load_release_gate_module()

    checks = module.build_check_commands()
    names = [check["name"] for check in checks]

    assert names[:4] == [
        "pytest",
        "stable_tool_smoke",
        "cli_help",
        "config_validate",
    ]


def test_build_check_commands_adds_remote_checks_when_host_is_given() -> None:
    module = _load_release_gate_module()

    checks = module.build_check_commands(host_id="demo-server")
    names = [check["name"] for check in checks]

    assert "preflight" in names
    assert "smoke_connect_only" in names


def test_build_check_commands_uses_new_stable_tool_contract() -> None:
    module = _load_release_gate_module()

    stable_smoke = next(check for check in module.build_check_commands() if check["name"] == "stable_tool_smoke")
    command = stable_smoke["command"]

    expected_section = command.split("expected = ", 1)[1].split("\n", 1)[0]
    assert "write_remote_file" not in expected_section
    assert "append_remote_file" not in expected_section
    assert "tail_system_log" in command
    assert "check_service_status" in command
