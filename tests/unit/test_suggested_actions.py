from __future__ import annotations

from agent_remote_bridge.utils.suggested_actions import suggested_actions_for_error


def test_suggested_actions_cover_new_session_and_path_errors() -> None:
    assert suggested_actions_for_error("session_closed")
    assert suggested_actions_for_error("session_expired")
    assert suggested_actions_for_error("path_not_allowed")
    assert suggested_actions_for_error("unsupported_remote_state")
