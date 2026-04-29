from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from agent_remote_bridge.models import AuditRecord
from agent_remote_bridge.stores.audit_store import AuditStore


def test_audit_store_round_trips_failure_stage(tmp_path: Path) -> None:
    store = AuditStore(tmp_path / "audit.db")
    record = AuditRecord(
        audit_id="aud_demo",
        timestamp=datetime.now(timezone.utc),
        host_id="demo",
        tool_name="preflight",
        summary="Remote preflight failed at banner",
        error_type="ssh_banner_error",
        failure_stage="banner",
    )

    store.write(record)
    loaded = store.list_recent(limit=1)[0]

    assert loaded.failure_stage == "banner"
