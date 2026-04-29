from __future__ import annotations

import json
from argparse import Namespace
from datetime import datetime, timezone
from pathlib import Path

from agent_remote_bridge import main
from agent_remote_bridge.models import SessionState
from agent_remote_bridge.stores.session_store import SessionStore


def test_session_recent_command_lists_saved_sessions(tmp_path: Path, monkeypatch, capsys) -> None:
    sqlite_path = tmp_path / "state.db"
    store = SessionStore(sqlite_path)
    now = datetime.now(timezone.utc)
    store.save(
        SessionState(
            session_id="sess_demo",
            host_id="demo",
            current_cwd="/root",
            created_at=now,
            updated_at=now,
        )
    )
    monkeypatch.setattr(
        main,
        "load_settings",
        lambda: type("Settings", (), {"sqlite_path": sqlite_path})(),
    )

    exit_code = main._session_recent_command(Namespace(limit=5, sqlite_path=None))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["count"] == 1
    assert payload["records"][0]["session_id"] == "sess_demo"


def test_session_cleanup_command_reports_deleted_count(tmp_path: Path, monkeypatch, capsys) -> None:
    sqlite_path = tmp_path / "state.db"
    store = SessionStore(sqlite_path)
    now = datetime.now(timezone.utc)
    store.save(
        SessionState(
            session_id="sess_closed",
            host_id="demo",
            status="closed",
            current_cwd="/root",
            created_at=now,
            updated_at=now.replace(year=now.year - 1),
        )
    )
    monkeypatch.setattr(
        main,
        "load_settings",
        lambda: type("Settings", (), {"sqlite_path": sqlite_path})(),
    )

    exit_code = main._session_cleanup_command(Namespace(max_age_hours=24, sqlite_path=None))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["deleted_count"] == 1
