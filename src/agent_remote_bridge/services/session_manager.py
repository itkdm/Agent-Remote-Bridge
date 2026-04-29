from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from agent_remote_bridge.models import HostConfig, SessionState
from agent_remote_bridge.stores.session_store import SessionStore
from agent_remote_bridge.utils.errors import SessionClosedError, SessionExpiredError


class SessionManager:
    def __init__(self, store: SessionStore, ttl_hours: int = 24) -> None:
        self._store = store
        self._ttl_hours = ttl_hours

    def open_session(self, host: HostConfig, notes: str | None = None) -> SessionState:
        now = datetime.now(timezone.utc)
        session = SessionState(
            session_id=f"sess_{uuid4().hex[:12]}",
            host_id=host.host_id,
            current_cwd=host.default_workdir,
            notes=notes,
            created_at=now,
            updated_at=now,
            expires_at=now + timedelta(hours=self._ttl_hours),
        )
        self._store.save(session)
        return session

    def get_session(self, session_id: str) -> SessionState:
        session = self._store.get(session_id)
        if session.status == "closed":
            raise SessionClosedError(f"Session '{session_id}' is closed and can no longer be used")
        expires_at = session.expires_at or (session.updated_at + timedelta(hours=self._ttl_hours))
        if expires_at <= datetime.now(timezone.utc):
            raise SessionExpiredError(f"Session '{session_id}' has expired and must be reopened")
        return session

    def close_session(self, session_id: str) -> SessionState:
        session = self._store.get(session_id)
        session.status = "closed"
        session.updated_at = datetime.now(timezone.utc)
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
        now = datetime.now(timezone.utc)
        session.updated_at = now
        session.expires_at = now + timedelta(hours=self._ttl_hours)
        self._store.save(session)
        return session
