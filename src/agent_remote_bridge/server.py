from __future__ import annotations

import inspect
from functools import wraps

from mcp.server.fastmcp import FastMCP

from agent_remote_bridge.adapters.ssh_adapter import SSHAdapter
from agent_remote_bridge.models import ResponseEnvelope
from agent_remote_bridge.services.audit_service import AuditService
from agent_remote_bridge.services.command_service import CommandService
from agent_remote_bridge.services.facts_service import FactsService
from agent_remote_bridge.services.file_service import FileService
from agent_remote_bridge.services.host_service import HostService
from agent_remote_bridge.services.network_service import NetworkService
from agent_remote_bridge.services.process_service import ProcessService
from agent_remote_bridge.services.security_guard import SecurityGuard
from agent_remote_bridge.services.session_manager import SessionManager
from agent_remote_bridge.services.system_service import SystemService
from agent_remote_bridge.settings import load_settings
from agent_remote_bridge.stores.audit_store import AuditStore
from agent_remote_bridge.stores.host_store import HostStore
from agent_remote_bridge.stores.session_store import SessionStore
from agent_remote_bridge.utils.errors import BridgeError
from agent_remote_bridge.utils.suggested_actions import suggested_actions_for_error

STABLE_TOOL_SUMMARY = [
    {
        "name": "exec_remote",
        "purpose": "Execute remote commands in the current session context.",
    },
    {
        "name": "read_remote_file",
        "purpose": "Read a remote file, optionally using head or tail mode.",
    },
    {
        "name": "list_remote_dir",
        "purpose": "List entries in a remote directory.",
    },
    {
        "name": "get_system_facts",
        "purpose": "Inspect the remote OS, runtime, package manager, and shell.",
    },
    {
        "name": "tail_system_log",
        "purpose": "Read recent system logs from the best available backend.",
    },
    {
        "name": "check_service_status",
        "purpose": "Check whether a remote service is running, inactive, failed, or missing.",
    },
]

EXPERIMENTAL_TOOL_SUMMARY = [
    {
        "name": "test_host_connection",
        "purpose": "Quickly verify SSH connectivity to a configured host.",
    },
    {
        "name": "tail_remote_logs",
        "purpose": "Tail a specific remote log file under allowed paths.",
    },
    {
        "name": "check_port_listening",
        "purpose": "Check whether a TCP port is listening.",
    },
    {
        "name": "inspect_processes",
        "purpose": "Find processes by keyword.",
    },
    {
        "name": "find_log_file",
        "purpose": "Search for likely log files using a keyword.",
    },
]


def _ok(message: str, data: dict | list | None = None, *, risk_flags: list[str] | None = None, truncated: bool = False) -> dict:
    return ResponseEnvelope(
        ok=True,
        message=message,
        data=data,
        risk_flags=risk_flags or [],
        truncated=truncated,
    ).model_dump(mode="json")


def _result_envelope(
    *,
    data: dict,
    success_message: str,
    failure_message: str,
) -> dict:
    ok = data.get("ok")
    if ok is None:
        ok = data.get("exit_code", 0) == 0
    error_type = data.get("error_type")
    if not ok and error_type is None:
        error_type = "remote_execution_failed"
    suggested_next_actions = list(data.get("suggested_next_actions", []))
    if not ok and not suggested_next_actions and error_type:
        suggested_next_actions = suggested_actions_for_error(error_type)
    return ResponseEnvelope(
        ok=bool(ok),
        message=success_message if ok else failure_message,
        data=data,
        suggested_next_actions=suggested_next_actions,
        risk_flags=list(data.get("risk_flags", [])),
        truncated=bool(data.get("truncated", False)),
        error_type=error_type,
    ).model_dump(mode="json")


def _error(
    message: str,
    *,
    error_type: str,
    risk_flags: list[str] | None = None,
    data: dict | list | None = None,
    truncated: bool = False,
) -> dict:
    return ResponseEnvelope(
        ok=False,
        message=message,
        data=data,
        suggested_next_actions=suggested_actions_for_error(error_type),
        risk_flags=risk_flags or [],
        truncated=truncated,
        error_type=error_type,
    ).model_dump(mode="json")


def _wrap_tool(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except BridgeError as exc:
            return _error(
                str(exc),
                error_type=exc.error_type,
                data=getattr(exc, "response_data", None),
            )
        except Exception as exc:  # pragma: no cover - defensive fallback
            return _error(str(exc), error_type="internal_error")

    wrapped.__signature__ = inspect.signature(fn)
    return wrapped


def create_server(
    *,
    host: str | None = None,
    port: int | None = None,
    log_level: str = "ERROR",
) -> FastMCP:
    settings = load_settings()
    host_store = HostStore(settings.host_config_path)
    session_store = SessionStore(settings.sqlite_path)
    audit_store = AuditStore(settings.sqlite_path)
    adapter = SSHAdapter()
    security_guard = SecurityGuard()
    audit_service = AuditService(audit_store)
    session_manager = SessionManager(session_store)
    command_service = CommandService(
        adapter=adapter,
        session_manager=session_manager,
        security_guard=security_guard,
        audit_service=audit_service,
    )
    file_service = FileService(
        adapter=adapter,
        security_guard=security_guard,
        audit_service=audit_service,
    )
    facts_service = FactsService(adapter)
    host_service = HostService(adapter=adapter, audit_service=audit_service)
    network_service = NetworkService(adapter=adapter, audit_service=audit_service)
    process_service = ProcessService(adapter=adapter, audit_service=audit_service)
    system_service = SystemService(adapter=adapter, audit_service=audit_service)

    server_kwargs = {
        "name": "Agent Remote Bridge",
        "instructions": (
            "Controlled SSH-backed remote execution for local coding agents. "
            "Prefer exec_remote for general tasks, and use the small set of structured observation tools "
            "only when they clearly reduce trial-and-error."
        ),
        "log_level": log_level,
    }
    if host is not None:
        server_kwargs["host"] = host
    if port is not None:
        server_kwargs["port"] = port

    server = FastMCP(**server_kwargs)

    @server.tool(description="List configured remote hosts that the bridge can connect to.")
    @_wrap_tool
    def list_hosts() -> dict:
        host_store.ensure_config_exists()
        hosts = [
            {
                "host_id": host.host_id,
                "alias": host.alias,
                "host": host.host,
                "username": host.username,
                "tags": host.tags,
                "default_workdir": host.default_workdir,
            }
            for host in host_store.list_hosts()
        ]
        return _ok("Hosts loaded successfully", hosts)

    @server.tool(description="Open a logical remote session and initialize its working context.")
    @_wrap_tool
    def open_session(host_id: str, notes: str | None = None) -> dict:
        host_store.ensure_config_exists()
        host = host_store.get_host(host_id)
        session = session_manager.open_session(host, notes=notes)
        detected_os = facts_service.detect_os_label(host)
        if detected_os:
            session = session_manager.update_after_command(
                session=session,
                command="detect_os",
                cwd_after=session.current_cwd,
                ok=True,
                detected_os=detected_os,
            )
        audit_service.record(
            host_id=host.host_id,
            session_id=session.session_id,
            tool_name="open_session",
            summary="Session opened",
        )
        return _ok(
            "Session opened successfully",
            {
                "session_id": session.session_id,
                "host_info": {
                    "host_id": host.host_id,
                    "username": host.username,
                    "host": host.host,
                },
                "detected_os": session.detected_os,
                "cwd": session.current_cwd,
                "capability_summary": STABLE_TOOL_SUMMARY
                + (EXPERIMENTAL_TOOL_SUMMARY if settings.enable_experimental_tools else []),
                "tool_tier": {
                    "stable_count": len(STABLE_TOOL_SUMMARY),
                    "experimental_enabled": settings.enable_experimental_tools,
                },
            },
        )

    @server.tool(description="Inspect the current state of a logical remote session.")
    @_wrap_tool
    def get_session_state(session_id: str) -> dict:
        session = session_manager.get_session(session_id)
        return _ok("Session loaded successfully", session.model_dump(mode="json"))

    @server.tool(description="Execute a remote shell command using the current session context.")
    @_wrap_tool
    def exec_remote(
        session_id: str,
        command: str,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        timeout_sec: int = 60,
        use_sudo: bool = False,
        require_approval: bool = False,
        capture_state: bool = True,
    ) -> dict:
        del capture_state
        session = session_manager.get_session(session_id)
        host = host_store.get_host(session.host_id)
        result = command_service.exec_remote(
            host=host,
            session=session,
            command=command,
            cwd=cwd,
            env=env,
            timeout_sec=timeout_sec,
            use_sudo=use_sudo,
            require_approval=require_approval,
        )
        return _result_envelope(
            data=result.model_dump(mode="json"),
            success_message="Command executed successfully",
            failure_message="Command failed",
        )

    @server.tool(description="Read a remote file within allowed paths, optionally using head or tail mode.")
    @_wrap_tool
    def read_remote_file(
        session_id: str,
        path: str,
        max_chars: int = 8000,
        head_lines: int | None = None,
        tail_lines: int | None = None,
    ) -> dict:
        session = session_manager.get_session(session_id)
        host = host_store.get_host(session.host_id)
        result = file_service.read_file_range(
            host=host,
            session=session,
            path=path,
            max_chars=max_chars,
            head_lines=head_lines,
            tail_lines=tail_lines,
        )
        return _result_envelope(
            data=result,
            success_message="Remote file read successfully",
            failure_message="Remote file read failed",
        )

    @server.tool(description="List entries in a remote directory within allowed paths.")
    @_wrap_tool
    def list_remote_dir(session_id: str, path: str) -> dict:
        session = session_manager.get_session(session_id)
        host = host_store.get_host(session.host_id)
        result = file_service.list_dir(host=host, session=session, path=path)
        return _result_envelope(
            data=result,
            success_message="Remote directory listed successfully",
            failure_message="Remote directory listing failed",
        )

    @server.tool(description="Fetch recent system logs using the best available backend.")
    @_wrap_tool
    def tail_system_log(session_id: str, lines: int = 100) -> dict:
        session = session_manager.get_session(session_id)
        host = host_store.get_host(session.host_id)
        result = file_service.tail_system_log(host=host, session=session, lines=lines)
        return _result_envelope(
            data=result,
            success_message="System logs fetched successfully",
            failure_message="System logs fetch failed",
        )

    @server.tool(description="Collect basic system facts such as OS, kernel, package manager, and shell.")
    @_wrap_tool
    def get_system_facts(session_id: str) -> dict:
        session = session_manager.get_session(session_id)
        host = host_store.get_host(session.host_id)
        facts = facts_service.get_system_facts(host)
        return _ok("System facts collected successfully", facts)

    @server.tool(description="Check the status of a remote service using the best available backend.")
    @_wrap_tool
    def check_service_status(session_id: str, service_name: str) -> dict:
        session = session_manager.get_session(session_id)
        host = host_store.get_host(session.host_id)
        result = system_service.check_service_status(
            host=host,
            session=session,
            service_name=service_name,
        )
        return _result_envelope(
            data=result,
            success_message="Service status fetched successfully",
            failure_message="Service status fetch failed",
        )

    @server.tool(description="Close a logical remote session.")
    @_wrap_tool
    def close_session(session_id: str) -> dict:
        session = session_manager.close_session(session_id)
        audit_service.record(
            host_id=session.host_id,
            session_id=session.session_id,
            tool_name="close_session",
            summary="Session closed",
        )
        return _ok("Session closed successfully", session.model_dump(mode="json"))

    if settings.enable_experimental_tools:
        @server.tool(description="Experimental: find likely log files under allowed log-related directories.")
        @_wrap_tool
        def find_log_file(session_id: str, keyword: str, max_results: int = 20) -> dict:
            session = session_manager.get_session(session_id)
            host = host_store.get_host(session.host_id)
            result = file_service.find_log_file(
                host=host,
                session=session,
                keyword=keyword,
                max_results=max_results,
            )
            return _result_envelope(
                data=result,
                success_message="Candidate log files fetched successfully",
                failure_message="Candidate log file lookup failed",
            )

        @server.tool(description="Experimental: tail a specific remote log file within allowed paths.")
        @_wrap_tool
        def tail_remote_logs(session_id: str, path: str, lines: int = 100) -> dict:
            session = session_manager.get_session(session_id)
            host = host_store.get_host(session.host_id)
            result = file_service.tail_logs(host=host, session=session, path=path, lines=lines)
            return _result_envelope(
                data=result,
                success_message="Remote logs fetched successfully",
                failure_message="Remote logs fetch failed",
            )

        @server.tool(description="Experimental: check whether a TCP port is currently listening on the remote host.")
        @_wrap_tool
        def check_port_listening(session_id: str, port: int) -> dict:
            session = session_manager.get_session(session_id)
            host = host_store.get_host(session.host_id)
            result = network_service.check_port_listening(
                host=host,
                session=session,
                port=port,
            )
            return _result_envelope(
                data=result,
                success_message="Port listening status fetched successfully",
                failure_message="Port listening status fetch failed",
            )

        @server.tool(description="Experimental: inspect remote processes by keyword.")
        @_wrap_tool
        def inspect_processes(session_id: str, keyword: str, limit: int = 30) -> dict:
            session = session_manager.get_session(session_id)
            host = host_store.get_host(session.host_id)
            result = process_service.inspect_processes(
                host=host,
                session=session,
                keyword=keyword,
                limit=limit,
            )
            return _result_envelope(
                data=result,
                success_message="Process inspection completed successfully",
                failure_message="Process inspection failed",
            )

        @server.tool(description="Experimental: test SSH connectivity for a configured host.")
        @_wrap_tool
        def test_host_connection(host_id: str, timeout_sec: int = 15) -> dict:
            host_store.ensure_config_exists()
            host = host_store.get_host(host_id)
            result = host_service.test_connection(host, timeout_sec=timeout_sec)
            return _result_envelope(
                data=result,
                success_message="Host connection test succeeded",
                failure_message="Host connection test failed",
            )

    return server
