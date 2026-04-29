from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from agent_remote_bridge.models import HostConfig, SessionState
from agent_remote_bridge.services.session_manager import SessionManager
from agent_remote_bridge.stores.session_store import SessionStore
from agent_remote_bridge.utils.errors import SessionClosedError, SessionExpiredError


def _host() -> HostConfig:
    return HostConfig(
        host_id="demo",
        host="127.0.0.1",
        username="root",
        auth_mode="password",
        password="secret",
        default_workdir="/root",
        allowed_paths=["/root"],
    )


def test_get_session_rejects_closed_session(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "state.db")
    now = datetime.now(timezone.utc)
    store.save(
        SessionState(
            session_id="sess_closed",
            host_id="demo",
            status="closed",
            current_cwd="/root",
            created_at=now,
            updated_at=now,
        )
    )
    manager = SessionManager(store, ttl_hours=24)

    with pytest.raises(SessionClosedError):
        manager.get_session("sess_closed")


def test_get_session_rejects_expired_open_session(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "state.db")
    now = datetime.now(timezone.utc)
    store.save(
        SessionState(
            session_id="sess_expired",
            host_id="demo",
            status="open",
            current_cwd="/root",
            created_at=now - timedelta(days=2),
            updated_at=now - timedelta(days=2),
        )
    )
    manager = SessionManager(store, ttl_hours=24)

    with pytest.raises(SessionExpiredError):
        manager.get_session("sess_expired")


def test_open_session_sets_expiration_timestamp(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "state.db")
    manager = SessionManager(store, ttl_hours=24)

    session = manager.open_session(_host())

    assert session.expires_at is not None
    assert session.expires_at > session.updated_at
