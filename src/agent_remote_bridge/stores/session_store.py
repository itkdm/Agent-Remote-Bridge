from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from agent_remote_bridge.models import SessionState
from agent_remote_bridge.utils.errors import NotFoundError


class SessionStore:
    def __init__(self, sqlite_path: Path) -> None:
        self._sqlite_path = sqlite_path
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._sqlite_path)

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    host_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    current_cwd TEXT NOT NULL,
                    env_delta_json TEXT NOT NULL,
                    detected_os TEXT,
                    privilege_level TEXT NOT NULL,
                    recent_commands_json TEXT NOT NULL,
                recent_failures_json TEXT NOT NULL,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                expires_at TEXT
                )
                """
            )
            columns = {row[1] for row in conn.execute("PRAGMA table_info(sessions)").fetchall()}
            if "expires_at" not in columns:
                conn.execute("ALTER TABLE sessions ADD COLUMN expires_at TEXT")

    def save(self, session: SessionState) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO sessions (
                    session_id, host_id, status, current_cwd, env_delta_json,
                    detected_os, privilege_level, recent_commands_json,
                    recent_failures_json, notes, created_at, updated_at
                    , expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.session_id,
                    session.host_id,
                    session.status,
                    session.current_cwd,
                    json.dumps(session.env_delta),
                    session.detected_os,
                    session.privilege_level,
                    json.dumps(session.recent_commands),
                    json.dumps(session.recent_failures),
                    session.notes,
                    session.created_at.isoformat(),
                    session.updated_at.isoformat(),
                    session.expires_at.isoformat() if session.expires_at else None,
                ),
            )

    def get(self, session_id: str) -> SessionState:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if row is None:
            raise NotFoundError(f"Session '{session_id}' not found")
        return self._row_to_model(row)

    def list_recent(self, limit: int = 20) -> list[SessionState]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM sessions ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_model(row) for row in rows]

    def cleanup_closed_before(self, cutoff: datetime) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM sessions WHERE status = ? AND updated_at < ?",
                ("closed", cutoff.isoformat()),
            )
            return int(cursor.rowcount or 0)

    def _row_to_model(self, row: tuple) -> SessionState:
        return SessionState(
            session_id=row[0],
            host_id=row[1],
            status=row[2],
            current_cwd=row[3],
            env_delta=json.loads(row[4]),
            detected_os=row[5],
            privilege_level=row[6],
            recent_commands=json.loads(row[7]),
            recent_failures=json.loads(row[8]),
            notes=row[9],
            created_at=datetime.fromisoformat(row[10]),
            updated_at=datetime.fromisoformat(row[11]),
            expires_at=datetime.fromisoformat(row[12]) if len(row) > 12 and row[12] else None,
        )
