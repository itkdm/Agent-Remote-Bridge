# Agent Remote Bridge

Agent Remote Bridge is a controlled MCP server that lets a local coding agent work against a real remote Linux host over SSH.

Agent Remote Bridge 是一个受控的 MCP Server，用来把远程 Linux 主机能力通过 SSH 安全接入本地 Coding Agent。

## What It Is / 它是什么

- Local-first: your MCP client runs locally, while the bridge reaches the remote host.
- Remote Linux only: the bridge targets real Linux environments, not local shell emulation.
- Non-interactive by design: sessions preserve context, but they are not persistent remote shells.
- Agent-oriented: it is built for MCP clients such as VS Code, Codex Desktop, Claude Desktop, and other agent runtimes.

- 本地优先：MCP 客户端运行在本机，由桥接服务连接远程主机。
- 面向真实 Linux：目标是远程 Linux 环境，而不是本地 shell 模拟。
- 默认非交互：会话保留上下文，但不是远程常驻 shell。
- 面向 Agent：适配 VS Code、Codex Desktop、Claude Desktop 及其他兼容 MCP 的客户端。

## Why Not Plain SSH / 为什么不是直接 SSH

Plain SSH is flexible, but it does not give an MCP agent stable tool contracts, structured diagnostics, bounded file operations, or local audit history.

直接 SSH 很灵活，但它无法天然提供 MCP Agent 需要的稳定工具契约、结构化诊断、受控文件操作和本地审计记录。

Agent Remote Bridge adds:

- logical sessions with cwd and lightweight context retention
- structured tool responses with `error_type` and suggestions
- path allowlists and risk-aware execution boundaries
- local audit and diagnostic commands such as `doctor`, `preflight`, and `audit recent`

Agent Remote Bridge 额外提供：

- 带 cwd 和轻量上下文保留的逻辑 session
- 带 `error_type` 和建议动作的结构化返回
- 路径白名单和风险感知的执行边界
- `doctor`、`preflight`、`audit recent` 等本地诊断和审计能力

## Who Should Use It / 适合谁使用

Use Agent Remote Bridge if you:

- build or operate MCP-enabled coding agents
- want a local agent to inspect or change a remote Linux environment
- need more control than ad-hoc SSH hopping
- prefer a small, explicit tool surface over a heavy remote automation platform

适合使用 Agent Remote Bridge 的场景：

- 你在构建或使用兼容 MCP 的 Coding Agent
- 你希望本地 Agent 能查看或操作远程 Linux 环境
- 你需要比临时 SSH 跳转更可控的方式
- 你希望工具面小而明确，而不是一个重型远程运维平台

Do **not** use it if you need:

- interactive TTY sessions
- non-Linux remote targets
- team RBAC or multi-tenant control planes
- Docker / Kubernetes / WinRM adapters today

如果你需要以下能力，目前不适合使用它：

- 交互式 TTY 会话
- 非 Linux 远程目标
- 团队 RBAC 或多租户控制平面
- Docker / Kubernetes / WinRM 适配器

## Quickstart / 快速开始

Install from source for now:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv\Scripts\python.exe -m pip install -e .
```

当前仓库内的最短安装路径仍然是源码安装；正式 PyPI 发布前，建议这样使用。

Create your local host config:

```powershell
Copy-Item .\config\hosts.example.yaml .\config\hosts.yaml
```

Set a password environment variable if you use password auth:

```powershell
$env:ARB_DEMO_SERVER_PASSWORD="YOUR_PASSWORD"
```

Validate locally before connecting:

```powershell
agent-remote-bridge config-validate
agent-remote-bridge preflight --host-id demo-server
```

Start the MCP server:

```powershell
agent-remote-bridge --transport stdio
```

Then use these first three actions:

1. `list_hosts`
2. `open_session(host_id="demo-server")`
3. `exec_remote(command="pwd")`

More guided first-run steps live in [QUICKSTART.md](./QUICKSTART.md).

更完整的首次接入步骤见 [QUICKSTART.md](./QUICKSTART.md)。

The tracked example config lives at [config/hosts.example.yaml](./config/hosts.example.yaml).

仓库中可直接查看的示例配置位于 [config/hosts.example.yaml](./config/hosts.example.yaml)。

## Stable vs Experimental / 稳定能力与实验能力

### Stable tools / 默认稳定工具

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

These are the default public contract. Behavior changes to them should come with tests, docs, and release notes.

这些工具构成默认公开契约。对它们的行为调整应同步带上测试、文档和发布说明。

### Experimental tools / 实验工具

- `test_host_connection`
- `tail_remote_logs`
- `check_port_listening`
- `inspect_processes`
- `find_log_file`
- `write_remote_file`
- `append_remote_file`

Experimental tools are opt-in and may evolve faster. Enable them only when they clearly reduce operator guesswork.

实验工具需要显式开启，演进速度可能更快。只有在它们确实能减少排障试探成本时才建议启用。

Enable experimental mode with:

```powershell
agent-remote-bridge --experimental-tools
```

or:

```powershell
$env:ARB_ENABLE_EXPERIMENTAL_TOOLS=1
```

## Security Model / 安全模型

Agent Remote Bridge is a **controlled remote execution bridge**, not a sandbox.

Agent Remote Bridge 是一个**受控远程执行桥**，不是沙箱。

Current guardrails include:

- host-scoped `allowed_paths`
- command risk classification
- explicit `sudo` policy
- session TTL and closed-session rejection
- local audit records with summaries, failure stages, and retry metadata

当前保护边界包括：

- 按主机配置的 `allowed_paths`
- 命令风险分级
- 显式 `sudo` 策略
- session TTL 与 closed session 拒绝执行
- 带摘要、失败阶段、重试信息的本地审计记录

`exec_remote` is intentionally powerful. Treat it as an escape hatch with policy, audit, and review around it.

`exec_remote` 是有意保留的强能力入口，应当和策略、审计、评审一起使用。

See [SECURITY.md](./SECURITY.md) for disclosure guidance.

安全报告和披露流程见 [SECURITY.md](./SECURITY.md)。

## Supported Platforms / 支持矩阵

### Local runtime / 本地运行环境

- Windows: supported
- macOS: supported
- Linux: supported
- Python: `3.11` and `3.12`

### Remote targets / 远程目标

- Linux only
- SSH only
- non-interactive command execution only

### Transports / 传输方式

- `stdio`
- `sse`
- `streamable-http`

## Repository Guide / 仓库导航

- [QUICKSTART.md](./QUICKSTART.md): first 5-minute setup
- [CLIENTS.md](./CLIENTS.md): client-specific integration examples
- [CONTRIBUTING.md](./CONTRIBUTING.md): development workflow and contribution rules
- [SUPPORT.md](./SUPPORT.md): support expectations and issue guidance
- [RELEASE.md](./RELEASE.md): release checklist and tagging flow

## Roadmap / 路线图

Current priorities:

1. Freeze the stable tool contract after this cleanup pass
2. Keep CI green across Windows, macOS, and Linux
3. Publish installable release artifacts
4. Keep docs, diagnostics, and release gates aligned

当前阶段的重点是：

1. 完成这轮收口后冻结稳定工具契约
2. 维持 Windows、macOS、Linux 三端 CI 绿色
3. 提供可安装的发布产物
4. 保持文档、诊断命令和 release gate 一致

## License

This project is released under the [MIT License](./LICENSE).
