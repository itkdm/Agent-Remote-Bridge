from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from agent_remote_bridge.models import HostConfig, SessionState
from agent_remote_bridge.stores.session_store import SessionStore


class SessionManager:
    def __init__(self, store: SessionStore) -> None:
        self._store = store

    def open_session(self, host: HostConfig, notes: str | None = None) -> SessionState:
        now = datetime.now().astimezone()
        session = SessionState(
            session_id=f"sess_{uuid4().hex[:12]}",
            host_id=host.host_id,
            current_cwd=host.default_workdir,
            notes=notes,
            created_at=now,
            updated_at=now,
        )
        self._store.save(session)
        return session

    def get_session(self, session_id: str) -> SessionState:
        return self._store.get(session_id)

    def close_session(self, session_id: str) -> SessionState:
        session = self._store.get(session_id)
        session.status = "closed"
        session.updated_at = datetime.now().astimezone()
        self._store.save(session)
        return session

    def update_after_command(
        self,
        *,
        session: SessionState,
        command: str,
        cwd_after: str,
        ok: bool,
        failure_summary: str | None = None,
        detected_os: str | None = None,
        env_delta: dict[str, str] | None = None,
    ) -> SessionState:
        session.current_cwd = cwd_after
        if env_delta:
            session.env_delta.update(env_delta)
        session.recent_commands = (session.recent_commands + [command])[-10:]
        if not ok and failure_summary:
            session.recent_failures = (session.recent_failures + [failure_summary])[-10:]
        if detected_os:
            session.detected_os = detected_os
        session.updated_at = datetime.now().astimezone()
        self._store.save(session)
        return session
