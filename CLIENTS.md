# 客户端接入示例

本文档展示如何把 Agent Remote Bridge 接入不同 MCP 客户端。

## VS Code

工作区级配置示例：

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

项目内已有示例：

- [.vscode/mcp.json](./.vscode/mcp.json)

## Codex Desktop

推荐直接使用项目的一键脚本：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_codex_mcp.ps1
```

这个脚本会：

- 启动本地 `streamable-http` MCP server
- 把 `http://127.0.0.1:8000/mcp` 注册到 Codex

运行后重启 Codex Desktop 即可。

如果你想手动配置，本地 `stdio` MCP server 也可以使用：

```text
command: powershell
args:
  - -ExecutionPolicy
  - Bypass
  - -File
  - D:\develop\project\Agent Remote Bridge\scripts\run_server.ps1
  - --transport
  - stdio
```

也可以直接调用项目虚拟环境里的 Python：

```text
command: D:\develop\project\Agent Remote Bridge\.venv\Scripts\python.exe
args:
  - -m
  - agent_remote_bridge.main
  - --transport
  - stdio
```

## Claude Desktop

如果客户端支持标准 MCP 本地进程配置，也可以用同样的 `stdio` 方式：

```text
command: D:\develop\project\Agent Remote Bridge\.venv\Scripts\python.exe
args:
  - -m
  - agent_remote_bridge.main
  - --transport
  - stdio
```

## HTTP 方式

如果客户端支持 HTTP MCP server，可先启动：

```powershell
agent-remote-bridge --transport streamable-http --host 127.0.0.1 --port 8000
```

然后连接：

```text
http://127.0.0.1:8000/mcp
```

如果客户端使用 SSE，也可以：

```powershell
agent-remote-bridge --transport sse --host 127.0.0.1 --port 8000
```
