# Agent Remote Bridge

Agent Remote Bridge 是一个标准 MCP Server，用来把远程 Linux 服务器能力接入本地 Agent。

它的核心价值是：

- 保留本地上下文
- 连接远程真实环境
- 让 Agent 执行命令、读取文件、查看日志、检查服务状态
- 用更受控的方式替代“手动 SSH 来回切换”

## 运行方式

默认推荐形态是：

- `Agent Remote Bridge` 运行在你的本地机器
- 它被 VS Code、Codex Desktop、Claude Desktop 或其他兼容 MCP 的客户端拉起
- 然后由它连接远程 Linux 服务器

默认架构如下：

```text
MCP Client (VS Code / Codex / Claude)
            ->
Agent Remote Bridge（本地运行）
            ->
SSH / Password / Key
            ->
Remote Linux Server
```

这也是最适合先落地的方式，因为它接入成本最低，调试最直接。

这个项目不是 VS Code 专属能力。只要客户端兼容 MCP，就都可以接入。

当前支持的传输方式：

- `stdio`
- `sse`
- `streamable-http`

因此可接入：

- VS Code
- Codex Desktop
- Claude Desktop
- 其他兼容 MCP 的客户端或 Agent 框架

## 当前范围

当前项目定位为：

- Linux only
- SSH/密码登录优先
- 非交互式命令执行
- 逻辑 session，而不是远程持久 shell

## 默认公开的稳定工具

默认情况下，服务只暴露稳定工具：

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

这套工具面是刻意收敛过的，核心原则是：

- 通用操作优先交给 `exec_remote`
- 只保留少量高价值、稳定的结构化工具

## 实验性工具

以下工具默认不公开，只有显式开启实验模式才会暴露：

- `test_host_connection`
- `tail_remote_logs`
- `check_port_listening`
- `inspect_processes`
- `find_log_file`

开启方式：

```powershell
agent-remote-bridge --experimental-tools
```

或：

```powershell
$env:ARB_ENABLE_EXPERIMENTAL_TOOLS=1
agent-remote-bridge
```

## 安装

### 方式一：使用项目内虚拟环境

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv\Scripts\python.exe -m pip install -e .
```

### 方式二：直接安装为命令行工具

```powershell
pip install -e .
```

安装后会提供命令：

```powershell
agent-remote-bridge
```

## 配置

复制示例配置：

```powershell
Copy-Item .\config\hosts.example.yaml .\config\hosts.yaml
```

然后修改 [config/hosts.yaml](./config/hosts.yaml)。

说明：

- `config/hosts.yaml` 是你的本地私有配置
- 对外分享时，以 `config/hosts.example.yaml` 为准
- 详细说明见 [config/README.md](./config/README.md)

推荐的密码登录示例：

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
    tags:
      - demo
      - linux
```

注意：

- 长期使用优先选择 `key_path` 或 `ssh_config`
- 如果使用 `key_path`，`config-validate` 会检查私钥文件是否存在于本机
- 当前仍支持密码登录
- 不建议把真实密码提交到仓库
- 推荐用 `password_env` 代替明文 `password`
- 密码登录模式会自动重试少量瞬时 SSH 建连抖动
- SSH 连接失败会尽量区分认证失败、banner 异常和连接异常
- SSH 相关错误返回会附带更直接的下一步排查建议

环境变量示例：

```powershell
$env:ARB_DEMO_SERVER_PASSWORD="YOUR_PASSWORD"
```

## 启动

### 1. 本地 `stdio` 启动

这是最适合桌面类 MCP 客户端的方式。

```powershell
agent-remote-bridge --transport stdio
```

或：

```powershell
python -m agent_remote_bridge.main --transport stdio
```

Windows 下也可以用项目脚本：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_server.ps1 --transport stdio
```

### 2. HTTP 启动

适合代理接入或多客户端场景。

```powershell
agent-remote-bridge --transport streamable-http --host 127.0.0.1 --port 8000
```

或者：

```powershell
agent-remote-bridge --transport sse --host 127.0.0.1 --port 8000
```

### 3. 指定自定义 SQLite 路径

```powershell
agent-remote-bridge --sqlite-path .\data\state.dev.db
```

### 4. 开启实验性工具

```powershell
agent-remote-bridge --experimental-tools
```

### 5. 检查本地 MCP server 状态

```powershell
agent-remote-bridge status
```

这个命令会检查：

- 本地 `127.0.0.1:8000` 是否在监听
- `http://127.0.0.1:8000/mcp` 是否可响应
- Codex 是否已经注册了 `agentRemoteBridge`

### 6. 停止本地 HTTP MCP server

```powershell
agent-remote-bridge stop
```

这个命令会停止由本项目启动的本地 `streamable-http` MCP server 进程。

### 7. 后台启动本地 HTTP MCP server

```powershell
agent-remote-bridge start
```

这个命令会在后台启动本地 `streamable-http` MCP server，并默认监听：

- `127.0.0.1:8000`
- `http://127.0.0.1:8000/mcp`

### 8. 注册到 Codex

```powershell
agent-remote-bridge codex-register
```

这个命令会把本地 MCP 地址注册到 Codex：

- 默认名称：`agentRemoteBridge`
- 默认地址：`http://127.0.0.1:8000/mcp`

### 9. 一次性诊断本地环境

```powershell
agent-remote-bridge doctor
```

这个命令会统一检查：

- `config/hosts.yaml` 是否存在
- 至少是否配置了 1 个主机
- 本地 HTTP MCP server 是否在线
- Codex 是否已经注册当前 MCP 地址
- 如果只配置了 1 个可用主机，或显式传入 `--preflight-host-id`，还会附带远程链路预检摘要

### 10. 查看最近本地审计记录

```powershell
agent-remote-bridge audit recent
```

这个命令支持查看最近的本地操作记录，也支持按主机、session、工具名和失败状态过滤。
对于 `exec_remote`，审计记录会保留执行耗时、是否触发 SSH 重试、stderr 首条摘要，以及当前可操作的下一步建议。

### 11. 校验本地主机配置

```powershell
agent-remote-bridge config-validate
```

这个命令会在真正连接远端之前检查 `config/hosts.yaml` 的结构、认证组合、路径配置和明显的占位值问题。
### 12. 运行远程连接预检

```powershell
agent-remote-bridge preflight --host-id demo-server
```

这个命令会按阶段检查：

- 主机配置是否有效
- DNS / IP 是否可解析
- TCP 22 端口是否可达
- SSH banner 是否正常
- 认证是否成功

## 命令行参数

```text
agent-remote-bridge [OPTIONS]

--transport {stdio,sse,streamable-http}
--host HOST
--port PORT
--sqlite-path PATH
--experimental-tools
--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}

agent-remote-bridge status [OPTIONS]

--host HOST
--port PORT
--codex-server-name NAME

agent-remote-bridge stop [OPTIONS]

--port PORT

agent-remote-bridge start [OPTIONS]

--host HOST
--port PORT
--sqlite-path PATH
--experimental-tools
--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}

agent-remote-bridge codex-register [OPTIONS]

--host HOST
--port PORT
--codex-server-name NAME

agent-remote-bridge doctor [OPTIONS]

--host HOST
--port PORT
--sqlite-path PATH
--experimental-tools
--codex-server-name NAME
--config-path PATH
--preflight-host-id HOST_ID
--preflight-timeout-sec N

agent-remote-bridge audit recent [OPTIONS]

--limit N
--host-id HOST_ID
--session-id SESSION_ID
--tool-name TOOL_NAME
--only-failures

agent-remote-bridge config-validate [OPTIONS]

--config-path PATH
--sqlite-path PATH
--experimental-tools

agent-remote-bridge preflight [OPTIONS]

--host-id HOST_ID
--timeout-sec N
--config-path PATH
--sqlite-path PATH
--experimental-tools
```

## 客户端接入

### VS Code

推荐通过工作区级 `.vscode/mcp.json` 让 VS Code 直接拉起本地 `stdio` server。

项目里已经提供了一个示例：

- [.vscode/mcp.json](./.vscode/mcp.json)

如果你使用项目自带虚拟环境，VS Code 最终拉起的是：

- [scripts/run_server.ps1](./scripts/run_server.ps1)

### 其他 MCP 客户端

如果客户端支持 `stdio` MCP server，只要配置它启动：

```powershell
agent-remote-bridge --transport stdio
```

即可接入。

如果客户端支持 HTTP MCP server，也可以连接：

```powershell
agent-remote-bridge --transport streamable-http --host 127.0.0.1 --port 8000
```

更完整的接入示例见：

- [CLIENTS.md](./CLIENTS.md)

如果你使用 Codex Desktop，项目也提供了一键接入脚本：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_codex_mcp.ps1
```

这个脚本会启动本地 HTTP MCP server，并把它注册到 Codex 的全局 MCP 配置。

## 推荐使用方式

1. 本地运行 `Agent Remote Bridge`
2. 使用 MCP 客户端接入本地 server
3. 由它连接远程 Linux 服务器
4. 优先使用稳定工具集
5. 复杂场景回退到 `exec_remote`

## 适合的场景

- 在本地使用 Agent，但需要操作远程 Linux 服务器
- 需要查看日志、检查服务状态、读取配置文件
- 希望把“本地上下文 + 远程执行”串成连续工作流
- 希望先以最小方式接入 MCP，再逐步扩展能力

## 当前状态

当前已经验证通过：

- 本地 MCP server 可运行
- VS Code 可接入
- 可真实连接远程服务器
- 可执行 `pwd`、`ls`、`cat`
- 可读取系统事实信息
- 可查看系统日志
- 可检查服务状态

## 快速开始

更适合第一次使用的版本见：

- [QUICKSTART.md](./QUICKSTART.md)

也可以直接运行本地 smoke test：

```powershell
python .\scripts\smoke_test.py --host-id demo-server --connect-only
python .\scripts\smoke_test.py --host-id demo-server
```

## License

本项目当前使用：

- [MIT License](./LICENSE)
