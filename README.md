# Agent Remote Bridge

[![CI](https://github.com/itkdm/Agent-Remote-Bridge/actions/workflows/ci.yml/badge.svg)](https://github.com/itkdm/Agent-Remote-Bridge/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

Agent Remote Bridge 是一个受控的 MCP Server，用来把远程 Linux 主机能力通过 SSH 安全接入本地 Coding Agent。

它的定位很明确：让本地 Agent 保留上下文，同时以更可控的方式操作真实的远程 Linux 环境。

## 它是什么

- 本地优先：MCP 客户端运行在本机，由桥接服务连接远程主机。
- 面向真实 Linux：目标是远程 Linux 环境，而不是本地 shell 模拟。
- 默认非交互：会话保留上下文，但不是远程常驻 shell。
- 面向 Agent：适配 VS Code、Codex Desktop、Claude Desktop 及其他兼容 MCP 的客户端。

## 为什么不是直接 SSH

直接 SSH 很灵活，但它无法天然提供 MCP Agent 需要的结构化工具响应、受控文件操作和本地审计记录。

Agent Remote Bridge 额外提供：

- 带 `cwd` 和轻量上下文保留的逻辑 session
- 带 `error_type` 和建议动作的结构化返回
- 路径白名单和风险感知的执行边界
- `doctor`、`preflight`、`audit recent` 等本地诊断和审计能力

## 适合谁使用

如果你符合下面这些场景，这个项目会比较合适：

- 你在构建或使用兼容 MCP 的 Coding Agent
- 你希望本地 Agent 能查看或操作远程 Linux 环境
- 你需要一种比临时 SSH 跳转更可控的方式
- 你更偏好小而明确的工具面，而不是完整的远程运维平台

如果你需要下面这些能力，它暂时不适合：

- 交互式 TTY 会话
- 非 Linux 远程目标
- 团队 RBAC 或多租户控制平面
- Docker / Kubernetes / WinRM 适配

## 快速开始

当前推荐通过源码安装：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv\Scripts\python.exe -m pip install -e .
```

复制示例配置：

```powershell
Copy-Item .\config\hosts.example.yaml .\config\hosts.yaml
```

如果使用密码认证，设置环境变量：

```powershell
$env:ARB_DEMO_SERVER_PASSWORD="YOUR_PASSWORD"
```

连接前先做本地校验：

```powershell
agent-remote-bridge config-validate
agent-remote-bridge preflight --host-id demo-server
```

启动 MCP Server：

```powershell
agent-remote-bridge --transport stdio
```

启动后，建议先试这三个动作：

1. `list_hosts`
2. `open_session(host_id="demo-server")`
3. `exec_remote(command="pwd")`

示例配置文件位于 [config/hosts.example.yaml](./config/hosts.example.yaml)。

## 默认工具

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

## 可选工具

以下工具默认不启用，适合在需要更深入诊断或受控写入远程文件时使用：

- `test_host_connection`
- `tail_remote_logs`
- `check_port_listening`
- `inspect_processes`
- `find_log_file`
- `write_remote_file`
- `append_remote_file`

开启方式：

```powershell
agent-remote-bridge --experimental-tools
```

或者：

```powershell
$env:ARB_ENABLE_EXPERIMENTAL_TOOLS=1
```

## 安全模型

Agent Remote Bridge 是一个受控远程执行桥，不是沙箱。

当前保护边界包括：

- 按主机配置的 `allowed_paths`
- 命令风险分级
- 显式 `sudo` 策略
- session TTL 与 closed session 拒绝执行
- 带摘要、失败阶段和重试信息的本地审计记录

`exec_remote` 是有意保留的强能力入口，建议配合策略、审计和评审一起使用。

## 支持矩阵

### 本地运行环境

- Windows
- macOS
- Linux
- Python `3.11` / `3.12`

### 远程目标

- Linux
- SSH
- 非交互式命令执行

### 传输方式

- `stdio`
- `sse`
- `streamable-http`

## 许可证

本项目基于 [MIT License](./LICENSE) 发布。
