from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent_remote_bridge.server import create_server  # noqa: E402


async def call_tool(server, name: str, arguments: dict) -> dict:
    result = await server.call_tool(name, arguments)
    if isinstance(result, dict):
        return result
    if isinstance(result, list) and result:
        first = result[0]
        text = getattr(first, "text", "")
        return json.loads(text) if text else {"ok": False, "message": "Empty tool response"}
    return {"ok": False, "message": "No tool response"}


async def main() -> int:
    parser = argparse.ArgumentParser(description="Run smoke tests against the local MCP server instance.")
    parser.add_argument("--host-id", default="staging-1", help="Configured host_id to test.")
    parser.add_argument("--connect-only", action="store_true", help="Only validate tool registration and SSH connectivity.")
    args = parser.parse_args()

    server = create_server()

    tools = await server.list_tools()
    tool_names = sorted(tool.name for tool in tools)
    print("tools:", ", ".join(tool_names))

    response = await call_tool(server, "list_hosts", {})
    print("list_hosts:", json.dumps(response, ensure_ascii=False, indent=2))
    if not response.get("ok"):
        return 1

    response = await call_tool(server, "test_host_connection", {"host_id": args.host_id})
    print("test_host_connection:", json.dumps(response, ensure_ascii=False, indent=2))
    if not response.get("ok"):
        return 1
    if not response.get("data", {}).get("ok"):
        return 2

    if args.connect_only:
        return 0

    response = await call_tool(server, "open_session", {"host_id": args.host_id, "notes": "smoke test"})
    print("open_session:", json.dumps(response, ensure_ascii=False, indent=2))
    if not response.get("ok"):
        return 1

    session_id = response["data"]["session_id"]
    response = await call_tool(
        server,
        "exec_remote",
        {
            "session_id": session_id,
            "command": "pwd && whoami && uname -a",
            "timeout_sec": 20,
        },
    )
    print("exec_remote:", json.dumps(response, ensure_ascii=False, indent=2))

    close_response = await call_tool(server, "close_session", {"session_id": session_id})
    print("close_session:", json.dumps(close_response, ensure_ascii=False, indent=2))

    return 0 if response.get("ok") else 3


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
