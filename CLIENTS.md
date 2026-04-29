# Client Integration / 客户端接入

This document shows how to connect Agent Remote Bridge from common MCP clients without depending on internal project context.

本文档说明如何把 Agent Remote Bridge 接入常见 MCP 客户端，并尽量避免依赖仓库内部上下文。

## Shared Rules / 共通规则

- Prefer the stable tool set by default.
- Treat experimental tools as opt-in diagnostics or controlled write helpers.
- Keep the bridge local; let it reach the remote Linux host over SSH.

- 默认优先使用稳定工具集合。
- 实验工具视为显式开启的诊断或受控写入能力。
- 桥接服务应运行在本地，再由它连接远程 Linux 主机。

## VS Code

Workspace-level example:

```json
{
  "servers": {
    "agent-remote-bridge": {
      "type": "stdio",
      "command": "powershell",
      "args": [
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        "${workspaceFolder}\\scripts\\run_server.ps1",
        "--transport",
        "stdio"
      ]
    }
  }
}
```

The repository already includes a starting point:

- [.vscode/mcp.json](./.vscode/mcp.json)

## Codex Desktop

Recommended local HTTP flow:

```powershell
agent-remote-bridge start
agent-remote-bridge codex-register
agent-remote-bridge status
```

The repository also ships a helper script:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_codex_mcp.ps1
```

Codex 默认地址：

- name: `agentRemoteBridge`
- url: `http://127.0.0.1:8000/mcp`

## Claude Desktop

Use local `stdio` configuration with either the project script or the Python module entrypoint:

```text
command: D:\develop\project\Agent Remote Bridge\.venv\Scripts\python.exe
args:
  - -m
  - agent_remote_bridge.main
  - --transport
  - stdio
```

## Other MCP Clients / 其他 MCP 客户端

If the client supports `stdio`, use:

```text
agent-remote-bridge --transport stdio
```

If the client supports HTTP MCP, start locally with:

```powershell
agent-remote-bridge --transport streamable-http --host 127.0.0.1 --port 8000
```

Then connect to:

```text
http://127.0.0.1:8000/mcp
```

## Stable Tool Contract / 默认稳定工具契约

- `list_hosts`
- `open_session`
- `get_session_state`
- `close_session`
- `exec_remote`
- `read_remote_file`
- `list_remote_dir`
- `get_system_facts`
- `tail_system_log`
- `check_service_status`

These are the tools clients should rely on by default.

这些工具是客户端默认可以依赖的契约。

## Experimental Tool Contract / 实验工具契约

- `test_host_connection`
- `tail_remote_logs`
- `check_port_listening`
- `inspect_processes`
- `find_log_file`
- `write_remote_file`
- `append_remote_file`

Only enable them when you have a concrete need for deeper diagnostics or controlled remote file writes.

只有在你确实需要更深入的诊断或受控远程写文件时，才建议启用这些工具。

## Recommended First Checks / 推荐先做的检查

```powershell
agent-remote-bridge config-validate
agent-remote-bridge preflight --host-id demo-server
agent-remote-bridge status
```

If something still feels off, continue with:

```powershell
agent-remote-bridge doctor
agent-remote-bridge audit recent
agent-remote-bridge session recent
```
