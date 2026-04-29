# 5-Minute Quickstart / 5 分钟上手

This guide is the shortest path to opening one remote session and running `pwd`.

这份指南只保留最短路径：打开一个远程 session，并执行一次 `pwd`。

## 1. Install / 安装

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv\Scripts\python.exe -m pip install -e .
```

## 2. Create a host config / 创建主机配置

```powershell
Copy-Item .\config\hosts.example.yaml .\config\hosts.yaml
```

Edit [`config/hosts.yaml`](./config/hosts.yaml) to match your server.

Then edit your new local `config/hosts.yaml` using [`config/hosts.example.yaml`](./config/hosts.example.yaml) as the tracked example.

然后以仓库内的 [`config/hosts.example.yaml`](./config/hosts.example.yaml) 为参考，修改你本地新生成的 `config/hosts.yaml`。

Minimal example:

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

Set the password locally:

```powershell
$env:ARB_DEMO_SERVER_PASSWORD="YOUR_PASSWORD"
```

## 3. Validate before connecting / 正式连接前先校验

```powershell
agent-remote-bridge config-validate
agent-remote-bridge preflight --host-id demo-server
```

Use `doctor` if you also want to check local HTTP MCP status and Codex registration:

```powershell
agent-remote-bridge doctor
```

如果你还想同时检查本地 HTTP MCP 服务状态和 Codex 注册情况，可以再运行：

```powershell
agent-remote-bridge doctor
```

## 4. Start the MCP server / 启动 MCP Server

Recommended local `stdio` mode:

```powershell
agent-remote-bridge --transport stdio
```

Windows helper script:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_server.ps1 --transport stdio
```

If you prefer local HTTP mode:

```powershell
agent-remote-bridge start
agent-remote-bridge status
```

## 5. Connect from a client / 在客户端接入

If your MCP client supports local `stdio`, point it at:

```text
agent-remote-bridge --transport stdio
```

If you use VS Code, start from [CLIENTS.md](./CLIENTS.md) or the provided `.vscode/mcp.json`.

如果你使用 VS Code，可以从 [CLIENTS.md](./CLIENTS.md) 或仓库自带的 `.vscode/mcp.json` 开始。

## 6. Run the first three actions / 先试这三个动作

1. `list_hosts`
2. `open_session(host_id="demo-server")`
3. `exec_remote(command="pwd")`

At this point you have the basic loop working.

到这里，最小闭环就已经跑通了。

## 7. Optional local diagnostics / 可选本地诊断

```powershell
agent-remote-bridge audit recent
agent-remote-bridge session recent
agent-remote-bridge session cleanup --max-age-hours 24
```

## 8. When to enable experimental tools / 何时开启实验工具

Default work should stay on the stable tool set.

默认情况下，建议优先使用稳定工具集合。

Enable experimental tools only if you explicitly need:

- focused remote log tailing
- port listening checks
- process inspection
- controlled remote file writes

只有在你明确需要以下能力时，才建议开启实验工具：

- 指定日志文件 tail
- 端口监听检查
- 进程检查
- 受控远程写文件

```powershell
agent-remote-bridge --experimental-tools
```
