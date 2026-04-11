from __future__ import annotations

from agent_remote_bridge.adapters.ssh_adapter import SSHAdapter
from agent_remote_bridge.models import CommandResult, HostConfig, SessionState
from agent_remote_bridge.services.audit_service import AuditService
from agent_remote_bridge.services.security_guard import SecurityGuard
from agent_remote_bridge.services.session_manager import SessionManager
from agent_remote_bridge.utils.shell_quote import quote
from agent_remote_bridge.utils.truncation import truncate_text


class CommandService:
    def __init__(
        self,
        *,
        adapter: SSHAdapter,
        session_manager: SessionManager,
        security_guard: SecurityGuard,
        audit_service: AuditService,
    ) -> None:
        self._adapter = adapter
        self._session_manager = session_manager
        self._security_guard = security_guard
        self._audit_service = audit_service

    def exec_remote(
        self,
        *,
        host: HostConfig,
        session: SessionState,
        command: str,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        timeout_sec: int = 60,
        use_sudo: bool = False,
        require_approval: bool = False,
    ) -> CommandResult:
        security = self._security_guard.check_command(
            host=host,
            command=command,
            use_sudo=use_sudo,
            require_approval=require_approval,
        )
        if not security.allowed:
            result = CommandResult(
                ok=False,
                exit_code=-1,
                duration_ms=0,
                cwd_after=cwd or session.current_cwd,
                summary=security.message or "Command blocked",
                error_type="command_blocked",
                risk_level=security.risk_level,
                risk_flags=security.risk_flags,
                suggested_next_actions=["review security policy", "narrow command scope"],
            )
            self._audit_service.record(
                host_id=host.host_id,
                session_id=session.session_id,
                tool_name="exec_remote",
                command=command,
                risk_level=security.risk_level,
                blocked=True,
                summary=result.summary,
                error_type=result.error_type,
            )
            return result

        effective_cwd = cwd or session.current_cwd
        merged_env = dict(session.env_delta)
        if env:
            merged_env.update(env)

        env_exports = " ".join(f"{name}={quote(value)}" for name, value in merged_env.items())
        env_prefix = f"export {env_exports} && " if env_exports else ""
        user_command = f"sudo {command}" if use_sudo else command
        remote_command = f"cd {quote(effective_cwd)} && {env_prefix}{user_command}"

        execution = self._adapter.execute(host, remote_command, timeout_sec=timeout_sec)
        stdout, stdout_truncated = truncate_text(execution.stdout)
        stderr, stderr_truncated = truncate_text(execution.stderr)
        truncated = stdout_truncated or stderr_truncated
        ok = execution.exit_code == 0
        summary = self._summarize(command, execution.exit_code, stderr, stdout)
        error_type = None if ok else "remote_execution_failed"

        result = CommandResult(
            ok=ok,
            exit_code=execution.exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_ms=execution.duration_ms,
            cwd_after=effective_cwd,
            truncated=truncated,
            summary=summary,
            error_type=error_type,
            risk_level=security.risk_level,
            risk_flags=security.risk_flags,
            state_delta={"cwd": effective_cwd},
            suggested_next_actions=self._suggest_next_actions(ok, command),
        )

        self._session_manager.update_after_command(
            session=session,
            command=command,
            cwd_after=effective_cwd,
            ok=ok,
            failure_summary=summary if not ok else None,
            env_delta=env,
        )
        self._audit_service.record(
            host_id=host.host_id,
            session_id=session.session_id,
            tool_name="exec_remote",
            command=command,
            risk_level=security.risk_level,
            blocked=False,
            exit_code=result.exit_code,
            summary=result.summary,
            error_type=result.error_type,
        )
        return result

    @staticmethod
    def _summarize(command: str, exit_code: int, stderr: str, stdout: str) -> str:
        if exit_code == 0:
            if stdout.strip():
                first_line = stdout.strip().splitlines()[0]
                return f"Command succeeded: {first_line[:120]}"
            return "Command executed successfully"
        if stderr.strip():
            return f"Command failed: {stderr.strip().splitlines()[0][:120]}"
        return f"Command failed with exit code {exit_code}: {command[:100]}"

    @staticmethod
    def _suggest_next_actions(ok: bool, command: str) -> list[str]:
        if ok:
            return ["inspect command output", "continue the remote task"]
        if "systemctl" in command:
            return ["inspect service logs", "check service status again"]
        return ["inspect stderr", "check remote logs or configuration"]
