from __future__ import annotations

from agent_remote_bridge.adapters.ssh_adapter import SSHAdapter
from agent_remote_bridge.models import HostConfig, SessionState
from agent_remote_bridge.services.audit_service import AuditService
from agent_remote_bridge.utils.suggested_actions import suggested_actions_for_error
from agent_remote_bridge.utils.truncation import truncate_text


class ProcessService:
    def __init__(self, *, adapter: SSHAdapter, audit_service: AuditService) -> None:
        self._adapter = adapter
        self._audit_service = audit_service

    def inspect_processes(
        self,
        *,
        host: HostConfig,
        session: SessionState,
        keyword: str,
        limit: int = 30,
    ) -> dict:
        normalized = keyword.lower()
        command = (
            "ps -eo pid,ppid,user,%cpu,%mem,comm,args --sort=-%cpu | "
            f"grep -i {self._quote_for_grep(keyword)} | grep -v grep | head -n {int(limit)}"
        )
        result = self._adapter.execute(host, command)
        stdout, stdout_truncated = truncate_text(result.stdout, max_chars=12000)
        stderr, stderr_truncated = truncate_text(result.stderr, max_chars=2000)
        processes: list[dict[str, str]] = []
        for line in stdout.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            parts = stripped.split(None, 6)
            if len(parts) >= 7:
                pid, ppid, user, cpu, mem, comm, args = parts
                if normalized in args.lower() or normalized in comm.lower():
                    processes.append(
                        {
                            "pid": pid,
                            "ppid": ppid,
                            "user": user,
                            "cpu_percent": cpu,
                            "mem_percent": mem,
                            "command": comm,
                            "args": args,
                        }
                    )

        found = len(processes) > 0
        summary = f"Found {len(processes)} processes matching '{keyword}'" if found else f"No processes matched '{keyword}'"
        self._audit_service.record(
            host_id=host.host_id,
            session_id=session.session_id,
            tool_name="inspect_processes",
            command=keyword,
            exit_code=0 if found else 1,
            summary=summary,
            error_type=None if found else "remote_execution_failed",
        )
        return {
            "keyword": keyword,
            "processes": processes,
            "content": stdout,
            "stderr": stderr,
            "summary": summary,
            "ok": found,
            "exit_code": 0 if found else 1,
            "truncated": stdout_truncated or stderr_truncated,
            "error_type": None if found else "remote_execution_failed",
            "suggested_next_actions": [] if found else suggested_actions_for_error("remote_execution_failed"),
        }

    @staticmethod
    def _quote_for_grep(value: str) -> str:
        return "'" + value.replace("'", "'\"'\"'") + "'"
