# 5 分钟上手

这份文档只讲最短路径：让你的 MCP 客户端连上本地 Agent Remote Bridge，然后在远程服务器上执行一次 `pwd`。

## 1. 安装

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv\Scripts\python.exe -m pip install -e .
```

## 2. 配置远程主机

复制示例配置：

```powershell
Copy-Item .\config\hosts.example.yaml .\config\hosts.yaml
```

把 [config/hosts.yaml](./config/hosts.yaml) 改成你自己的服务器信息。

最小示例：

```yaml
hosts:
  - host_id: demo-server
    alias: demo
    host: YOUR_SERVER_IP
    port: 22
    username: root
    auth_mode: password
    password: YOUR_PASSWORD
    default_workdir: /root
    allowed_paths:
      - /root
      - /etc
      - /tmp
      - /var/log
    allow_sudo: true
```

## 3. 启动 MCP Server

```powershell
agent-remote-bridge --transport stdio
```

Windows 下也可以：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_server.ps1 --transport stdio
```

如果你已经用 HTTP 方式启动，也可以随时检查本地服务状态：

```powershell
agent-remote-bridge status
```

如果你想停掉本地 HTTP MCP server：

```powershell
agent-remote-bridge stop
```

## 4. 在客户端里接入

如果客户端支持本地 `stdio` MCP server，就让它启动：

```text
agent-remote-bridge --transport stdio
```

如果你使用 VS Code，可以直接用项目里的：

- [.vscode/mcp.json](./.vscode/mcp.json)

如果你使用 Codex Desktop，最短路径是直接运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_codex_mcp.ps1
```

运行后重启 Codex Desktop 即可。

## 5. 先试这三个动作

1. `list_hosts`
2. `open_session(host_id="demo-server")`
3. `exec_remote(command="pwd")`

## 6. 如果想快速验证

```powershell
python .\scripts\smoke_test.py --host-id demo-server
```

如果成功，你会看到：

- 主机连接成功
- session 打开成功
- 远程 `pwd` 返回结果
