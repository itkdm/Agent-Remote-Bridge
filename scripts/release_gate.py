from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def build_check_commands(host_id: str | None = None) -> list[dict[str, str]]:
    checks = [
        {
            "name": "pytest",
            "command": f'"{sys.executable}" -m pytest',
        },
        {
            "name": "stable_tool_smoke",
            "command": (
                f"@'\n"
                "import asyncio\n"
                "from agent_remote_bridge.server import create_server\n"
                "server = create_server()\n"
                "tools = asyncio.run(server.list_tools())\n"
                "names = {tool.name for tool in tools}\n"
                "expected = {'list_hosts', 'open_session', 'get_session_state', 'close_session', 'exec_remote', "
                "'read_remote_file', 'write_remote_file', 'append_remote_file', 'list_remote_dir', 'get_system_facts', "
                "'tail_system_log', 'check_service_status'}\n"
                "unexpected = names & {'test_host_connection', 'tail_remote_logs', 'check_port_listening', 'inspect_processes', 'find_log_file'}\n"
                "missing = expected - names\n"
                "assert not missing, f'Missing stable tools: {sorted(missing)}'\n"
                "assert not unexpected, f'Experimental tools unexpectedly enabled: {sorted(unexpected)}'\n"
                "print('stable tool smoke ok')\n"
                f"'@ | \"{sys.executable}\" -"
            ),
        },
        {
            "name": "cli_help",
            "command": f'"{sys.executable}" -m agent_remote_bridge.main --help',
        },
        {
            "name": "config_validate",
            "command": f'"{sys.executable}" -m agent_remote_bridge.main config-validate',
        },
    ]
    if host_id:
        checks.extend(
            [
                {
                    "name": "preflight",
                    "command": f'"{sys.executable}" -m agent_remote_bridge.main preflight --host-id {host_id} --timeout-sec 5',
                },
                {
                    "name": "smoke_connect_only",
                    "command": f'"{sys.executable}" .\\scripts\\smoke_test.py --host-id {host_id} --connect-only',
                },
            ]
        )
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the standard local release gate checks.")
    parser.add_argument("--host-id", default=None, help="Optional configured host_id for remote preflight and connect-only smoke.")
    parser.add_argument("--dry-run", action="store_true", help="Only print the release gate steps without executing them.")
    args = parser.parse_args()

    checks = build_check_commands(host_id=args.host_id)
    for check in checks:
        print(f"[{check['name']}] {check['command']}")
        if args.dry_run:
            continue
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", check["command"]],
            cwd=str(ROOT),
            check=False,
        )
        if completed.returncode != 0:
            return completed.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
