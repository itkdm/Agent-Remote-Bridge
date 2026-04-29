from __future__ import annotations

from pathlib import Path

from agent_remote_bridge.services.audit_service import AuditService
from agent_remote_bridge.stores.audit_store import AuditStore


def test_audit_service_preserves_failure_stage_in_recent_records(tmp_path: Path) -> None:
    service = AuditService(AuditStore(tmp_path / "audit.db"))

    service.record(
        host_id="demo",
        tool_name="preflight",
        summary="Remote preflight failed at banner",
        error_type="ssh_banner_error",
        failure_stage="banner",
    )
    records = service.list_recent(limit=1, only_failures=True)

    assert records[0]["failure_stage"] == "banner"
