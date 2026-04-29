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
    password_env: ARB_DEMO_SERVER_PASSWORD
    default_workdir: /root
    allowed_paths:
      - /root
      - /etc
      - /tmp
      - /var/log
    allow_sudo: true
```

然后在本地设置环境变量：

```powershell
$env:ARB_DEMO_SERVER_PASSWORD="YOUR_PASSWORD"
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

如果你想直接在后台启动本地 HTTP MCP server：

```powershell
agent-remote-bridge start
```

如果你想把本地 MCP 地址注册到 Codex：

```powershell
agent-remote-bridge codex-register
```

如果你想一次性检查本地环境：

```powershell
agent-remote-bridge doctor
```

如果你想查看最近的本地操作记录：

```powershell
agent-remote-bridge audit recent
```

如果你想查看最近的本地 session：

```powershell
agent-remote-bridge session recent
```

如果你想清理已关闭且过期的 session：

```powershell
agent-remote-bridge session cleanup --max-age-hours 24
```

如果你想在真正连接远端前先检查配置：

```powershell
agent-remote-bridge config-validate
```

如果你想在真正执行命令前先确认远程连通链路：

```powershell
agent-remote-bridge preflight --host-id demo-server
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

默认推荐先围绕稳定工具集工作；只有在需要更强排障辅助时，再显式开启实验工具。

## 6. 如果想快速验证

```powershell
python .\scripts\smoke_test.py --host-id demo-server
```

如果成功，你会看到：

- 主机连接成功
- session 打开成功
- 远程 `pwd` 返回结果
