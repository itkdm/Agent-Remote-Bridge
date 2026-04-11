from __future__ import annotations

import sqlite3
from pathlib import Path

from agent_remote_bridge.models import AuditRecord


class AuditStore:
    def __init__(self, sqlite_path: Path) -> None:
        self._sqlite_path = sqlite_path
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._sqlite_path)

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_records (
                    audit_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    host_id TEXT NOT NULL,
                    session_id TEXT,
                    tool_name TEXT NOT NULL,
                    command TEXT,
                    risk_level TEXT NOT NULL,
                    blocked INTEGER NOT NULL,
                    exit_code INTEGER,
                    summary TEXT NOT NULL,
                    error_type TEXT
                )
                """
            )

    def write(self, record: AuditRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO audit_records (
                    audit_id, timestamp, host_id, session_id, tool_name, command,
                    risk_level, blocked, exit_code, summary, error_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.audit_id,
                    record.timestamp.isoformat(),
                    record.host_id,
                    record.session_id,
                    record.tool_name,
                    record.command,
                    record.risk_level,
                    int(record.blocked),
                    record.exit_code,
                    record.summary,
                    record.error_type,
                ),
            )
