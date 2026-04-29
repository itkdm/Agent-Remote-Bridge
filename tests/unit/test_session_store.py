from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from agent_remote_bridge.models import SessionState
from agent_remote_bridge.stores.session_store import SessionStore


def test_session_store_round_trips_session_state(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "state.db")
    now = datetime.now(timezone.utc)
    session = SessionState(
        session_id="sess_demo",
        host_id="demo",
        current_cwd="/srv/app",
        env_delta={"APP_ENV": "test"},
        detected_os="ubuntu",
        recent_commands=["pwd"],
        recent_failures=["boom"],
        notes="note",
        created_at=now,
        updated_at=now,
    )

    store.save(session)
    loaded = store.get("sess_demo")

    assert loaded == session


def test_session_store_lists_most_recent_first(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "state.db")
    now = datetime.now(timezone.utc)
    older = SessionState(
        session_id="sess_older",
        host_id="demo",
        current_cwd="/tmp",
        created_at=now,
        updated_at=now,
    )
    newer = SessionState(
        session_id="sess_newer",
        host_id="demo",
        current_cwd="/srv",
        created_at=now + timedelta(minutes=1),
        updated_at=now + timedelta(minutes=1),
    )

    store.save(older)
    store.save(newer)
    sessions = store.list_recent()

    assert [session.session_id for session in sessions[:2]] == ["sess_newer", "sess_older"]
