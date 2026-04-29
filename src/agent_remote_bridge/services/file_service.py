from __future__ import annotations

from agent_remote_bridge.adapters.ssh_adapter import SSHAdapter
from agent_remote_bridge.models import HostConfig, SessionState
from agent_remote_bridge.services.audit_service import AuditService
from agent_remote_bridge.services.security_guard import SecurityGuard
from agent_remote_bridge.utils.errors import SecurityError
from agent_remote_bridge.utils.remote_path import resolve_remote_path
from agent_remote_bridge.utils.shell_quote import quote
from agent_remote_bridge.utils.suggested_actions import suggested_actions_for_error
from agent_remote_bridge.utils.truncation import truncate_text


class FileService:
    def __init__(
        self,
        *,
        adapter: SSHAdapter,
        security_guard: SecurityGuard,
        audit_service: AuditService,
    ) -> None:
        self._adapter = adapter
        self._security_guard = security_guard
        self._audit_service = audit_service

    def read_file(self, *, host: HostConfig, session: SessionState, path: str, max_chars: int = 8000) -> dict:
        return self.read_file_range(
            host=host,
            session=session,
            path=path,
            max_chars=max_chars,
            head_lines=None,
            tail_lines=None,
        )

    def read_file_range(
        self,
        *,
        host: HostConfig,
        session: SessionState,
        path: str,
        max_chars: int = 8000,
        head_lines: int | None = None,
        tail_lines: int | None = None,
    ) -> dict:
        resolved_path = resolve_remote_path(session.current_cwd, path)
        self._enforce_path(host, resolved_path)
        read_command = f"cat {quote(resolved_path)}"
        range_mode = "full"
        if head_lines is not None and head_lines > 0:
            read_command = f"head -n {int(head_lines)} {quote(resolved_path)}"
            range_mode = "head"
        elif tail_lines is not None and tail_lines > 0:
            read_command = f"tail -n {int(tail_lines)} {quote(resolved_path)}"
            range_mode = "tail"
        command = (
            f"if [ -f {quote(resolved_path)} ]; then "
            f"wc -l {quote(resolved_path)} | awk '{{print $1}}'; "
            f"wc -c {quote(resolved_path)} | awk '{{print $1}}'; "
            f"{read_command}; "
            "else "
            "printf '__ARB_NOT_FILE__'; "
            "fi"
        )
        result = self._adapter.execute(host, command)
        content, truncated = truncate_text(result.stdout, max_chars=max_chars)
        stderr, stderr_truncated = truncate_text(result.stderr, max_chars=2000)
        line_count = None
        size_bytes = None
        body = content
        if result.exit_code == 0 and not content.startswith("__ARB_NOT_FILE__"):
            parts = content.splitlines()
            if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
                line_count = int(parts[0])
                size_bytes = int(parts[1])
                body = "\n".join(parts[2:])
        summary = "File read successfully" if result.exit_code == 0 else "File read failed"
        if content.startswith("__ARB_NOT_FILE__"):
            summary = "Path is not a regular file"
        self._audit_service.record(
            host_id=host.host_id,
            session_id=session.session_id,
            tool_name="read_remote_file",
            command=f"cat {resolved_path}",
            exit_code=result.exit_code,
            summary=summary,
            error_type=None if result.exit_code == 0 else "remote_execution_failed",
        )
        return {
            "path": path,
            "resolved_path": resolved_path,
            "content": body,
            "range_mode": range_mode,
            "truncated": truncated or stderr_truncated,
            "summary": summary,
            "exit_code": result.exit_code,
            "stderr": stderr,
            "line_count": line_count,
            "size_bytes": size_bytes,
            "head_lines": head_lines,
            "tail_lines": tail_lines,
            "error_type": None if result.exit_code == 0 else "remote_execution_failed",
            "suggested_next_actions": [] if result.exit_code == 0 else suggested_actions_for_error("remote_execution_failed"),
        }

    def list_dir(self, *, host: HostConfig, session: SessionState, path: str) -> dict:
        resolved_path = resolve_remote_path(session.current_cwd, path)
        self._enforce_path(host, resolved_path)
        command = (
            f"if [ -d {quote(resolved_path)} ]; then "
            f"find {quote(resolved_path)} -maxdepth 1 -mindepth 1 "
            "-printf '%y\\t%f\\t%s\\n' | sort; "
            "else "
            "printf '__ARB_NOT_DIR__'; "
            "fi"
        )
        result = self._adapter.execute(host, command)
        content, truncated = truncate_text(result.stdout)
        stderr, stderr_truncated = truncate_text(result.stderr, max_chars=2000)
        summary = "Directory listed successfully" if result.exit_code == 0 else "Directory listing failed"
        entries: list[dict[str, str | int]] = []
        if result.exit_code == 0 and not content.startswith("__ARB_NOT_DIR__"):
            for line in content.splitlines():
                parts = line.split("\t")
                if len(parts) == 3:
                    kind, name, size = parts
                    entries.append(
                        {
                            "name": name,
                            "entry_type": {"d": "dir", "f": "file", "l": "link"}.get(kind, kind),
                            "size_bytes": int(size) if size.isdigit() else size,
                        }
                    )
        if content.startswith("__ARB_NOT_DIR__"):
            summary = "Path is not a directory"
        self._audit_service.record(
            host_id=host.host_id,
            session_id=session.session_id,
            tool_name="list_remote_dir",
            command=f"find {resolved_path} -maxdepth 1",
            exit_code=result.exit_code,
            summary=summary,
            error_type=None if result.exit_code == 0 else "remote_execution_failed",
        )
        return {
            "path": path,
            "resolved_path": resolved_path,
            "entries": entries,
            "content": content,
            "truncated": truncated or stderr_truncated,
            "summary": summary,
            "exit_code": result.exit_code,
            "stderr": stderr,
            "error_type": None if result.exit_code == 0 else "remote_execution_failed",
            "suggested_next_actions": [] if result.exit_code == 0 else suggested_actions_for_error("remote_execution_failed"),
        }

    def tail_logs(self, *, host: HostConfig, session: SessionState, path: str, lines: int = 100) -> dict:
        resolved_path = resolve_remote_path(session.current_cwd, path)
        self._enforce_path(host, resolved_path)
        result = self._adapter.execute(host, f"tail -n {int(lines)} {quote(resolved_path)}")
        content, truncated = truncate_text(result.stdout)
        stderr, stderr_truncated = truncate_text(result.stderr, max_chars=2000)
        summary = "Log tail fetched successfully" if result.exit_code == 0 else "Log tail failed"
        last_line = None
        if content.strip():
            last_line = content.strip().splitlines()[-1][:200]
        if result.exit_code != 0 and stderr.strip():
            summary = f"Log tail failed: {stderr.strip().splitlines()[0][:160]}"
        self._audit_service.record(
            host_id=host.host_id,
            session_id=session.session_id,
            tool_name="tail_remote_logs",
            command=f"tail -n {int(lines)} {resolved_path}",
            exit_code=result.exit_code,
            summary=summary,
            error_type=None if result.exit_code == 0 else "remote_execution_failed",
        )
        return {
            "path": path,
            "resolved_path": resolved_path,
            "content": content,
            "truncated": truncated or stderr_truncated,
            "summary": summary,
            "exit_code": result.exit_code,
            "stderr": stderr,
            "last_line": last_line,
            "error_type": None if result.exit_code == 0 else "remote_execution_failed",
            "suggested_next_actions": [] if result.exit_code == 0 else suggested_actions_for_error("remote_execution_failed"),
        }

    def tail_system_log(self, *, host: HostConfig, session: SessionState, lines: int = 100) -> dict:
        candidates = [
            ("journalctl", f"journalctl -n {int(lines)} --no-pager"),
            ("/var/log/syslog", f"tail -n {int(lines)} /var/log/syslog"),
            ("/var/log/messages", f"tail -n {int(lines)} /var/log/messages"),
        ]
        errors: list[str] = []
        for source, command in candidates:
            result = self._adapter.execute(host, command)
            content, truncated = truncate_text(result.stdout)
            stderr, stderr_truncated = truncate_text(result.stderr, max_chars=2000)
            if result.exit_code == 0 and content.strip():
                summary = f"System logs fetched successfully from {source}"
                self._audit_service.record(
                    host_id=host.host_id,
                    session_id=session.session_id,
                    tool_name="tail_system_log",
                    command=command,
                    exit_code=result.exit_code,
                    summary=summary,
                )
                return {
                    "source": source,
                    "content": content,
                    "truncated": truncated or stderr_truncated,
                    "summary": summary,
                    "exit_code": result.exit_code,
                    "stderr": stderr,
                    "last_line": content.strip().splitlines()[-1][:200] if content.strip() else None,
                    "error_type": None,
                    "suggested_next_actions": [],
                }
            if stderr.strip():
                errors.append(f"{source}: {stderr.strip().splitlines()[0][:160]}")

        summary = "System log lookup failed"
        if errors:
            summary = f"{summary}: {'; '.join(errors)}"
        self._audit_service.record(
            host_id=host.host_id,
            session_id=session.session_id,
            tool_name="tail_system_log",
            command="journalctl/syslog/messages",
            exit_code=1,
            summary=summary,
            error_type="remote_execution_failed",
        )
        return {
            "source": None,
            "content": "",
            "truncated": False,
            "summary": summary,
            "exit_code": 1,
            "stderr": "\n".join(errors),
            "last_line": None,
            "error_type": "remote_execution_failed",
            "suggested_next_actions": suggested_actions_for_error("remote_execution_failed"),
        }

    def find_log_file(
        self,
        *,
        host: HostConfig,
        session: SessionState,
        keyword: str,
        max_results: int = 20,
    ) -> dict:
        preferred_roots = [path for path in host.allowed_paths if "/log" in path or path.startswith("/var")]
        fallback_roots = [path for path in host.allowed_paths if path not in preferred_roots]
        search_roots = []
        for path in preferred_roots + [session.current_cwd] + fallback_roots + ["/var/log"]:
            if path not in search_roots:
                search_roots.append(path)

        keyword_results: list[dict[str, str | int]] = []
        generic_results: list[dict[str, str | int]] = []
        errors: list[str] = []
        normalized_keyword = keyword.lower()
        for root in search_roots:
            check = self._security_guard.check_path(host=host, path=root)
            if not check.allowed:
                continue
            for mode in ("keyword", "generic"):
                expression = f"-iname '*{normalized_keyword}*'" if mode == "keyword" else "-iname '*.log'"
                command = (
                    f"if [ -d {quote(root)} ]; then "
                    f"find {quote(root)} -type f "
                    f"\\( {expression} \\) "
                    "-printf '%p\t%s\n' 2>/dev/null | head -n "
                    f"{int(max_results)}; "
                    "fi"
                )
                result = self._adapter.execute(host, command)
                if result.stderr.strip():
                    errors.append(result.stderr.strip().splitlines()[0][:160])
                if result.exit_code == 0 and result.stdout.strip():
                    for line in result.stdout.splitlines():
                        parts = line.split("\t")
                        if len(parts) == 2:
                            path, size = parts
                            item = {
                                "path": path,
                                "size_bytes": int(size) if size.isdigit() else size,
                            }
                            if mode == "keyword":
                                keyword_results.append(item)
                            else:
                                generic_results.append(item)

        results = keyword_results if keyword_results else generic_results

        unique_results: list[dict[str, str | int]] = []
        seen: set[str] = set()
        for item in results:
            path = str(item["path"])
            if path not in seen:
                unique_results.append(item)
                seen.add(path)
            if len(unique_results) >= max_results:
                break

        summary = f"Found {len(unique_results)} candidate log files for '{keyword}'"
        self._audit_service.record(
            host_id=host.host_id,
            session_id=session.session_id,
            tool_name="find_log_file",
            command=keyword,
            exit_code=0 if unique_results else 1,
            summary=summary,
            error_type=None if unique_results else "remote_execution_failed",
        )
        return {
            "keyword": keyword,
            "results": unique_results,
            "searched_roots": search_roots,
            "summary": summary,
            "stderr": "\n".join(errors),
            "ok": bool(unique_results),
            "error_type": None if unique_results else "remote_execution_failed",
            "suggested_next_actions": [] if unique_results else suggested_actions_for_error("remote_execution_failed"),
        }

    def _enforce_path(self, host: HostConfig, path: str) -> None:
        check = self._security_guard.check_path(host=host, path=path)
        if not check.allowed:
            raise SecurityError(check.message or "Path is not allowed")
