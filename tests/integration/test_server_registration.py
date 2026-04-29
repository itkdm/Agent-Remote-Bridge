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
    assert {
        "test_host_connection",
        "tail_remote_logs",
        "check_port_listening",
        "inspect_processes",
        "find_log_file",
    }.isdisjoint(tool_names)


def test_create_server_registers_experimental_tools_only_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("ARB_ENABLE_EXPERIMENTAL_TOOLS", "1")
    server = create_server()

    tools = asyncio.run(server.list_tools())
    tool_names = {tool.name for tool in tools}

    assert {
        "test_host_connection",
        "tail_remote_logs",
        "check_port_listening",
        "inspect_processes",
        "find_log_file",
    }.issubset(tool_names)
