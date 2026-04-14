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

    def list_recent(
        self,
        *,
        limit: int = 20,
        host_id: str | None = None,
        session_id: str | None = None,
        tool_name: str | None = None,
        only_failures: bool = False,
    ) -> list[AuditRecord]:
        query = """
            SELECT
                audit_id,
                timestamp,
                host_id,
                session_id,
                tool_name,
                command,
                risk_level,
                blocked,
                exit_code,
                summary,
                error_type
            FROM audit_records
            WHERE 1 = 1
        """
        params: list[object] = []
        if host_id:
            query += " AND host_id = ?"
            params.append(host_id)
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        if tool_name:
            query += " AND tool_name = ?"
            params.append(tool_name)
        if only_failures:
            query += " AND (blocked = 1 OR error_type IS NOT NULL OR (exit_code IS NOT NULL AND exit_code != 0))"
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()

        records: list[AuditRecord] = []
        for row in rows:
            records.append(
                AuditRecord(
                    audit_id=row[0],
                    timestamp=row[1],
                    host_id=row[2],
                    session_id=row[3],
                    tool_name=row[4],
                    command=row[5],
                    risk_level=row[6],
                    blocked=bool(row[7]),
                    exit_code=row[8],
                    summary=row[9],
                    error_type=row[10],
                )
            )
        return records
