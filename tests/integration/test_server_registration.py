from __future__ import annotations

import asyncio

from agent_remote_bridge.server import create_server


def test_create_server_registers_stable_tools() -> None:
    server = create_server()

    tools = asyncio.run(server.list_tools())
    tool_names = {tool.name for tool in tools}

    assert {
        "list_hosts",
        "open_session",
        "get_session_state",
        "close_session",
        "exec_remote",
        "read_remote_file",
        "list_remote_dir",
        "get_system_facts",
        "tail_system_log",
        "check_service_status",
    }.issubset(tool_names)
