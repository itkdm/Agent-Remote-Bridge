from __future__ import annotations

from agent_remote_bridge.server import _result_envelope


def test_result_envelope_marks_failed_command_result_as_error() -> None:
    payload = _result_envelope(
        data={
            "ok": False,
            "summary": "Command failed: permission denied",
            "error_type": "remote_execution_failed",
            "suggested_next_actions": ["inspect stderr"],
            "risk_flags": ["high_risk_command"],
            "truncated": True,
        },
        success_message="Command executed successfully",
        failure_message="Command failed",
    )

    assert payload["ok"] is False
    assert payload["message"] == "Command failed"
    assert payload["error_type"] == "remote_execution_failed"
    assert payload["suggested_next_actions"] == ["inspect stderr"]
    assert payload["risk_flags"] == ["high_risk_command"]
    assert payload["truncated"] is True


def test_result_envelope_keeps_success_payload_stable() -> None:
    payload = _result_envelope(
        data={
            "ok": True,
            "summary": "Command succeeded",
            "risk_flags": [],
            "truncated": False,
        },
        success_message="Command executed successfully",
        failure_message="Command failed",
    )

    assert payload["ok"] is True
    assert payload["message"] == "Command executed successfully"
    assert payload["error_type"] is None
    assert payload["suggested_next_actions"] == []
