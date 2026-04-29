from __future__ import annotations

from agent_remote_bridge.server import _error, _ok


def test_ok_response_envelope_has_expected_shape() -> None:
    payload = _ok("done", {"answer": 42}, risk_flags=["info"], truncated=True)

    assert payload == {
        "ok": True,
        "message": "done",
        "data": {"answer": 42},
        "warnings": [],
        "suggested_next_actions": [],
        "risk_flags": ["info"],
        "truncated": True,
        "error_type": None,
    }


def test_error_response_envelope_includes_error_type_and_suggestions() -> None:
    payload = _error("missing", error_type="config_error")

    assert payload["ok"] is False
    assert payload["message"] == "missing"
    assert payload["error_type"] == "config_error"
    assert payload["suggested_next_actions"]
