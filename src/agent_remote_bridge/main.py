from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from agent_remote_bridge.server import create_server
from agent_remote_bridge.services.audit_service import AuditService
from agent_remote_bridge.services.host_service import HostService
from agent_remote_bridge.settings import load_settings
from agent_remote_bridge.stores.audit_store import AuditStore
from agent_remote_bridge.stores.host_store import HostStore


def _apply_runtime_env(args: argparse.Namespace) -> None:
    if getattr(args, "sqlite_path", None):
        os.environ["ARB_SQLITE_PATH"] = args.sqlite_path
    if getattr(args, "experimental_tools", False):
        os.environ["ARB_ENABLE_EXPERIMENTAL_TOOLS"] = "1"


def _probe_tcp(host: str, port: int, timeout_sec: float = 1.5) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout_sec)
        return sock.connect_ex((host, port)) == 0


def _probe_http_mcp(url: str, timeout_sec: float = 3.0) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {},
            }
        ).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:
            body = response.read().decode("utf-8", errors="replace")
            return {
                "ok": True,
                "status_code": response.status,
                "detail": "MCP endpoint responded successfully",
                "body_preview": body[:200],
            }
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        healthy_http_error = exc.code in {400, 406} and (
            "Missing session ID" in detail or "Not Acceptable" in detail
        )
        return {
            "ok": healthy_http_error,
            "status_code": exc.code,
            "detail": detail[:200] or str(exc),
        }
    except Exception as exc:  # pragma: no cover - defensive fallback
        return {
            "ok": False,
            "status_code": None,
            "detail": str(exc),
        }


def _read_codex_server_status(server_name: str, url: str) -> dict[str, Any]:
    config_path = Path.home() / ".codex" / "config.toml"
    if not config_path.exists():
        return {
            "registered": False,
            "config_path": str(config_path),
            "detail": "Codex config file not found",
        }

    content = config_path.read_text(encoding="utf-8", errors="replace")
    section = f"[mcp_servers.{server_name}]"
    registered = section in content and f'url = "{url}"' in content
    return {
        "registered": registered,
        "config_path": str(config_path),
        "detail": "Server found in Codex config" if registered else "Server not found in Codex config",
    }


def _run_codex_command(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    executable = "codex"
    if os.name == "nt":
        executable = "codex.cmd"
    return subprocess.run(
        [executable, *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def _find_local_http_server_pids(port: int) -> list[int]:
    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        (
            f"$pids = Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
            "Select-Object -ExpandProperty OwningProcess -Unique; "
            "foreach ($procId in $pids) { "
            '$proc = Get-CimInstance Win32_Process -Filter "ProcessId = $procId"; '
            "if ($proc -and $proc.Name -eq 'python.exe' -and "
            "$proc.CommandLine -like '*agent_remote_bridge.main*' -and "
            "$proc.CommandLine -like '*streamable-http*') { "
            "Write-Output $procId "
            "} "
            "}"
        ),
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if completed.returncode != 0:
        return []
    pids: list[int] = []
    for line in completed.stdout.splitlines():
        line = line.strip()
        if line.isdigit():
            pids.append(int(line))
    return pids


def _start_command(args: argparse.Namespace) -> int:
    existing_pids = _find_local_http_server_pids(args.port)
    payload: dict[str, Any] = {
        "ok": True,
        "mode": "start",
        "host": args.host,
        "port": args.port,
        "transport": "streamable-http",
        "mcp_url": f"http://{args.host}:{args.port}/mcp",
        "started_pid": None,
        "message": "",
    }

    if existing_pids:
        payload["started_pid"] = existing_pids[0]
        payload["message"] = "Local Agent Remote Bridge HTTP server is already running."
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    project_root = Path.cwd()
    data_dir = project_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    stdout_log = data_dir / "local-mcp-http.out.log"
    stderr_log = data_dir / "local-mcp-http.err.log"

    command = [
        sys.executable,
        "-m",
        "agent_remote_bridge.main",
        "serve",
        "--transport",
        "streamable-http",
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--log-level",
        args.log_level,
    ]
    if args.sqlite_path:
        command.extend(["--sqlite-path", args.sqlite_path])
    if args.experimental_tools:
        command.append("--experimental-tools")

    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS

    with stdout_log.open("ab") as stdout_handle, stderr_log.open("ab") as stderr_handle:
        process = subprocess.Popen(
            command,
            cwd=str(project_root),
            stdin=subprocess.DEVNULL,
            stdout=stdout_handle,
            stderr=stderr_handle,
            close_fds=True,
            creationflags=creationflags,
        )
        payload["started_pid"] = process.pid

    for _ in range(12):
        if _probe_tcp(args.host, args.port):
            payload["message"] = "Started local Agent Remote Bridge HTTP server."
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0

        time.sleep(0.5)

    payload["ok"] = False
    payload["message"] = "Failed to start local Agent Remote Bridge HTTP server."
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 1


def _stop_command(args: argparse.Namespace) -> int:
    pids = _find_local_http_server_pids(args.port)
    payload: dict[str, Any] = {
        "ok": True,
        "mode": "stop",
        "port": args.port,
        "stopped_pids": [],
        "message": "",
    }
    if not pids:
        payload["message"] = "No local Agent Remote Bridge HTTP server process found."
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    stopped: list[int] = []
    for proc_id in pids:
        try:
            os.kill(proc_id, 9)
            stopped.append(proc_id)
        except OSError as exc:
            payload["ok"] = False
            payload["message"] = f"Failed to stop process {proc_id}: {exc}"
            payload["stopped_pids"] = stopped
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 1

    payload["stopped_pids"] = stopped
    payload["message"] = "Stopped local Agent Remote Bridge HTTP server."
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _status_command(args: argparse.Namespace) -> int:
    url = f"http://{args.host}:{args.port}/mcp"
    tcp_ok = _probe_tcp(args.host, args.port)
    http_probe = _probe_http_mcp(url) if tcp_ok else {
        "ok": False,
        "status_code": None,
        "detail": "Port is not listening",
    }
    codex_status = _read_codex_server_status(args.codex_server_name, url)

    payload = {
        "ok": tcp_ok and http_probe["ok"],
        "mode": "status",
        "transport": "streamable-http",
        "host": args.host,
        "port": args.port,
        "mcp_url": url,
        "tcp_listening": tcp_ok,
        "http_probe": http_probe,
        "codex": codex_status,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["ok"] else 1


def _codex_register_command(args: argparse.Namespace) -> int:
    url = f"http://{args.host}:{args.port}/mcp"
    list_result = _run_codex_command(["mcp", "list"])
    if list_result.returncode != 0:
        payload = {
            "ok": False,
            "mode": "codex-register",
            "server_name": args.codex_server_name,
            "mcp_url": url,
            "message": "Failed to inspect existing Codex MCP servers.",
            "stderr": list_result.stderr.strip(),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1

    if args.codex_server_name in list_result.stdout:
        remove_result = _run_codex_command(["mcp", "remove", args.codex_server_name])
        if remove_result.returncode != 0:
            payload = {
                "ok": False,
                "mode": "codex-register",
                "server_name": args.codex_server_name,
                "mcp_url": url,
                "message": "Failed to replace existing Codex MCP server registration.",
                "stderr": remove_result.stderr.strip(),
            }
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 1

    add_result = _run_codex_command(["mcp", "add", args.codex_server_name, "--url", url])
    payload = {
        "ok": add_result.returncode == 0,
        "mode": "codex-register",
        "server_name": args.codex_server_name,
        "mcp_url": url,
        "message": "Registered MCP server in Codex." if add_result.returncode == 0 else "Failed to register MCP server in Codex.",
        "stdout": add_result.stdout.strip(),
        "stderr": add_result.stderr.strip(),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if add_result.returncode == 0 else 1


def _doctor_command(args: argparse.Namespace) -> int:
    _apply_runtime_env(args)
    settings = load_settings()
    url = f"http://{args.host}:{args.port}/mcp"
    host_store = HostStore(settings.host_config_path)
    config_validation = host_store.validate_config()

    tcp_ok = _probe_tcp(args.host, args.port)
    http_probe = _probe_http_mcp(url) if tcp_ok else {
        "ok": False,
        "status_code": None,
        "detail": "Port is not listening",
    }
    codex_status = _read_codex_server_status(args.codex_server_name, url)
    issues: list[str] = []
    issues.extend(config_validation["errors"])
    if not (tcp_ok and http_probe["ok"]):
        issues.append("Local HTTP MCP server is not running.")
    if not codex_status["registered"]:
        issues.append("Codex is not registered to the current MCP URL.")

    payload = {
        "ok": len(issues) == 0,
        "mode": "doctor",
        "summary": {
            "config_exists": config_validation["path"] is not None and settings.host_config_path.exists(),
            "host_count": config_validation["host_count"],
            "local_http_running": tcp_ok and http_probe["ok"],
            "codex_registered": codex_status["registered"],
        },
        "issues": issues,
        "config": {
            "host_config_path": str(settings.host_config_path),
            "sqlite_path": str(settings.sqlite_path),
            "exists": settings.host_config_path.exists(),
            "errors": config_validation["errors"],
            "warnings": config_validation["warnings"],
        },
        "hosts": {
            "count": config_validation["host_count"],
            "host_ids": [item["host_id"] for item in config_validation["hosts"][:10] if "host_id" in item],
            "validation": config_validation["hosts"],
        },
        "local_http": {
            "host": args.host,
            "port": args.port,
            "mcp_url": url,
            "tcp_listening": tcp_ok,
            "http_probe": http_probe,
        },
        "codex": codex_status,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["ok"] else 1


def _config_validate_command(args: argparse.Namespace) -> int:
    _apply_runtime_env(args)
    settings = load_settings()
    config_path = Path(args.config_path) if args.config_path else settings.host_config_path
    host_store = HostStore(config_path)
    validation = host_store.validate_config()
    payload = {
        "ok": validation["ok"],
        "mode": "config_validate",
        "path": validation["path"],
        "host_count": validation["host_count"],
        "errors": validation["errors"],
        "warnings": validation["warnings"],
        "hosts": validation["hosts"],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["ok"] else 1


def _preflight_command(args: argparse.Namespace) -> int:
    _apply_runtime_env(args)
    settings = load_settings()
    config_path = Path(args.config_path) if args.config_path else settings.host_config_path
    host_store = HostStore(config_path)
    audit_store = AuditStore(settings.sqlite_path)
    audit_service = AuditService(audit_store)
    validation = host_store.validate_config()

    stage_config = {
        "name": "config",
        "ok": False,
        "detail": "",
        "error_type": None,
    }
    matching_host = next((item for item in validation["hosts"] if item["host_id"] == args.host_id), None)
    if not validation["ok"] and not matching_host:
        stage_config["detail"] = f"Host '{args.host_id}' is not present in {validation['path']}"
        stage_config["error_type"] = "config_error"
        payload = {
            "ok": False,
            "mode": "preflight",
            "host_id": args.host_id,
            "summary": "Remote preflight failed at config",
            "stages": [stage_config],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1

    if matching_host and matching_host["ok"]:
        stage_config["ok"] = True
        stage_config["detail"] = "Host config is valid"
    else:
        errors = matching_host["errors"] if matching_host else [f"Host '{args.host_id}' not found"]
        stage_config["detail"] = "; ".join(errors)
        stage_config["error_type"] = "config_error"
        payload = {
            "ok": False,
            "mode": "preflight",
            "host_id": args.host_id,
            "summary": "Remote preflight failed at config",
            "stages": [stage_config],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1

    from agent_remote_bridge.adapters.ssh_adapter import SSHAdapter

    host_service = HostService(adapter=SSHAdapter(), audit_service=audit_service)
    host = host_store.get_host(args.host_id)
    result = host_service.preflight(host, timeout_sec=args.timeout_sec)
    result["mode"] = "preflight"
    result["stages"] = [stage_config, *result["stages"]]
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


def _audit_recent_command(args: argparse.Namespace) -> int:
    _apply_runtime_env(args)
    settings = load_settings()
    audit_store = AuditStore(settings.sqlite_path)
    audit_service = AuditService(audit_store)
    records = audit_service.list_recent(
        limit=args.limit,
        host_id=args.host_id,
        session_id=args.session_id,
        tool_name=args.tool_name,
        only_failures=args.only_failures,
    )
    payload = {
        "ok": True,
        "mode": "audit_recent",
        "filters": {
            "limit": args.limit,
            "host_id": args.host_id,
            "session_id": args.session_id,
            "tool_name": args.tool_name,
            "only_failures": args.only_failures,
        },
        "count": len(records),
        "records": records,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _serve_command(args: argparse.Namespace) -> int:
    _apply_runtime_env(args)
    server = create_server(
        host=args.host,
        port=args.port,
        log_level=args.log_level,
    )
    server.run(transport=args.transport)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-remote-bridge",
        description="Agent Remote Bridge MCP server",
    )
    subparsers = parser.add_subparsers(dest="command")

    serve_parser = subparsers.add_parser("serve", help="Start the MCP server.")
    serve_parser.set_defaults(func=_serve_command)
    serve_parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="MCP transport to serve. Default: stdio",
    )
    serve_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind host for HTTP-based transports. Default: 127.0.0.1",
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Bind port for HTTP-based transports. Default: 8000",
    )
    serve_parser.add_argument(
        "--sqlite-path",
        default=None,
        help="Override SQLite state path. Useful for tests or multiple local instances.",
    )
    serve_parser.add_argument(
        "--experimental-tools",
        action="store_true",
        help="Expose experimental tools in addition to the stable tool set.",
    )
    serve_parser.add_argument(
        "--log-level",
        default="ERROR",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Server log level. Default: ERROR",
    )

    status_parser = subparsers.add_parser("status", help="Check local HTTP MCP server status.")
    status_parser.set_defaults(func=_status_command)
    status_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Target host for the local HTTP MCP server. Default: 127.0.0.1",
    )
    status_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Target port for the local HTTP MCP server. Default: 8000",
    )
    status_parser.add_argument(
        "--codex-server-name",
        default="agentRemoteBridge",
        help="Codex MCP server name to check in ~/.codex/config.toml. Default: agentRemoteBridge",
    )

    stop_parser = subparsers.add_parser("stop", help="Stop the local HTTP MCP server process.")
    stop_parser.set_defaults(func=_stop_command)
    stop_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Target port for the local HTTP MCP server. Default: 8000",
    )

    start_parser = subparsers.add_parser("start", help="Start the local HTTP MCP server in the background.")
    start_parser.set_defaults(func=_start_command)
    start_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind host for the local HTTP MCP server. Default: 127.0.0.1",
    )
    start_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Bind port for the local HTTP MCP server. Default: 8000",
    )
    start_parser.add_argument(
        "--sqlite-path",
        default=None,
        help="Override SQLite state path for the local HTTP MCP server.",
    )
    start_parser.add_argument(
        "--experimental-tools",
        action="store_true",
        help="Expose experimental tools in the local HTTP MCP server.",
    )
    start_parser.add_argument(
        "--log-level",
        default="ERROR",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Server log level. Default: ERROR",
    )

    codex_register_parser = subparsers.add_parser(
        "codex-register",
        help="Register the local HTTP MCP server URL in Codex.",
    )
    codex_register_parser.set_defaults(func=_codex_register_command)
    codex_register_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host for the local HTTP MCP server. Default: 127.0.0.1",
    )
    codex_register_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for the local HTTP MCP server. Default: 8000",
    )
    codex_register_parser.add_argument(
        "--codex-server-name",
        default="agentRemoteBridge",
        help="Codex MCP server name to register. Default: agentRemoteBridge",
    )

    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Run a local environment diagnostic for Agent Remote Bridge.",
    )
    doctor_parser.set_defaults(func=_doctor_command)
    doctor_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host for the local HTTP MCP server. Default: 127.0.0.1",
    )
    doctor_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for the local HTTP MCP server. Default: 8000",
    )
    doctor_parser.add_argument(
        "--sqlite-path",
        default=None,
        help="Override SQLite state path during diagnostics.",
    )
    doctor_parser.add_argument(
        "--experimental-tools",
        action="store_true",
        help="Reflect experimental tool mode during diagnostics.",
    )
    doctor_parser.add_argument(
        "--codex-server-name",
        default="agentRemoteBridge",
        help="Codex MCP server name to check. Default: agentRemoteBridge",
    )

    config_validate_parser = subparsers.add_parser(
        "config-validate",
        help="Validate local host configuration before connecting to remote hosts.",
    )
    config_validate_parser.set_defaults(func=_config_validate_command)
    config_validate_parser.add_argument(
        "--sqlite-path",
        default=None,
        help="Override SQLite state path during validation.",
    )
    config_validate_parser.add_argument(
        "--config-path",
        default=None,
        help="Validate a specific host config file instead of the default config/hosts.yaml.",
    )
    config_validate_parser.add_argument(
        "--experimental-tools",
        action="store_true",
        help="Reflect experimental tool mode during validation.",
    )

    preflight_parser = subparsers.add_parser(
        "preflight",
        help="Run a structured remote connectivity preflight for a configured host.",
    )
    preflight_parser.set_defaults(func=_preflight_command)
    preflight_parser.add_argument(
        "--host-id",
        required=True,
        help="Configured host_id to preflight.",
    )
    preflight_parser.add_argument(
        "--timeout-sec",
        type=int,
        default=15,
        help="Timeout in seconds for each preflight stage. Default: 15",
    )
    preflight_parser.add_argument(
        "--config-path",
        default=None,
        help="Use a specific host config file instead of the default config/hosts.yaml.",
    )
    preflight_parser.add_argument(
        "--sqlite-path",
        default=None,
        help="Override SQLite state path during preflight.",
    )
    preflight_parser.add_argument(
        "--experimental-tools",
        action="store_true",
        help="Reflect experimental tool mode during preflight.",
    )

    audit_parser = subparsers.add_parser(
        "audit",
        help="Inspect local audit records.",
    )
    audit_subparsers = audit_parser.add_subparsers(dest="audit_command")

    audit_recent_parser = audit_subparsers.add_parser(
        "recent",
        help="Show recent local audit records.",
    )
    audit_recent_parser.set_defaults(func=_audit_recent_command)
    audit_recent_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of audit records to return. Default: 20",
    )
    audit_recent_parser.add_argument(
        "--host-id",
        default=None,
        help="Filter by host_id.",
    )
    audit_recent_parser.add_argument(
        "--session-id",
        default=None,
        help="Filter by session_id.",
    )
    audit_recent_parser.add_argument(
        "--tool-name",
        default=None,
        help="Filter by tool_name.",
    )
    audit_recent_parser.add_argument(
        "--only-failures",
        action="store_true",
        help="Only include blocked or failed audit records.",
    )

    parser.set_defaults(func=_serve_command)
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="MCP transport to serve. Default: stdio",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind host for HTTP-based transports. Default: 127.0.0.1",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Bind port for HTTP-based transports. Default: 8000",
    )
    parser.add_argument(
        "--sqlite-path",
        default=None,
        help="Override SQLite state path. Useful for tests or multiple local instances.",
    )
    parser.add_argument(
        "--experimental-tools",
        action="store_true",
        help="Expose experimental tools in addition to the stable tool set.",
    )
    parser.add_argument(
        "--log-level",
        default="ERROR",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Server log level. Default: ERROR",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
