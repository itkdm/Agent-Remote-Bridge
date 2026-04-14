from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from agent_remote_bridge.server import create_server


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
