# Agent Remote Bridge

[English README](./README.en.md)

[![CI](https://github.com/itkdm/Agent-Remote-Bridge/actions/workflows/ci.yml/badge.svg)](https://github.com/itkdm/Agent-Remote-Bridge/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

Agent Remote Bridge 是一个受控的 MCP Server，用来把远程 Linux 主机能力通过 SSH 安全接入本地 Coding Agent。

它的定位很明确：让本地 Agent 保留上下文，同时以更可控的方式操作真实的远程 Linux 环境。

当前项目处于 `0.2.x beta` 阶段：核心能力已经可用，但稳定契约仍在持续收口。

## 它是什么

- 本地优先：MCP 客户端运行在本机，由桥接服务连接远程主机。
- 面向真实 Linux：目标是远程 Linux 环境，而不是本地 shell 模拟。
- 默认非交互：会话保留上下文，但不是远程常驻 shell。
- 面向 Agent：适配 VS Code、Codex Desktop、Claude Desktop 及其他兼容 MCP 的客户端。

## 为什么不是直接 SSH

直接 SSH 很灵活，但它无法天然提供 MCP Agent 需要的稳定工具契约、结构化诊断、受控文件操作和本地审计记录。

Agent Remote Bridge 额外提供：

- 带 cwd 和轻量上下文保留的逻辑 session
- 带 `error_type` 和建议动作的结构化返回
- 路径白名单和风险感知的执行边界
- `doctor`、`preflight`、`audit recent` 等本地诊断和审计能力

## 适合谁使用

适合使用 Agent Remote Bridge 的场景：

- 你在构建或使用兼容 MCP 的 Coding Agent
- 你希望本地 Agent 能查看或操作远程 Linux 环境
- 你需要比临时 SSH 跳转更可控的方式
- 你希望工具面小而明确，而不是一个重型远程运维平台

如果你需要以下能力，目前不适合使用它：

- 交互式 TTY 会话
- 非 Linux 远程目标
- 团队 RBAC 或多租户控制平面
- Docker / Kubernetes / WinRM 适配器

## 快速开始

当前版本更适合通过源码安装试用；在正式发布到 PyPI 之前，建议使用下面这条路径：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv\Scripts\python.exe -m pip install -e .
```

创建本地主机配置：

```powershell
Copy-Item .\config\hosts.example.yaml .\config\hosts.yaml
```

如果使用密码认证，设置环境变量：

```powershell
$env:ARB_DEMO_SERVER_PASSWORD="YOUR_PASSWORD"
```

正式连接前，先做本地校验：

```powershell
agent-remote-bridge config-validate
agent-remote-bridge preflight --host-id demo-server
```

启动 MCP Server：

```powershell
agent-remote-bridge --transport stdio
```

完成启动后，优先尝试这三个动作：

1. `list_hosts`
2. `open_session(host_id="demo-server")`
3. `exec_remote(command="pwd")`

更完整的首次接入步骤见 [QUICKSTART.md](./QUICKSTART.md)。

仓库中可直接查看的示例配置位于 [config/hosts.example.yaml](./config/hosts.example.yaml)。

## 稳定能力与实验能力

### 默认稳定工具

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

这些工具构成默认公开契约。后续如果调整它们的行为，项目会同步提供测试、文档和发布说明。

### 实验工具

- `test_host_connection`
- `tail_remote_logs`
- `check_port_listening`
- `inspect_processes`
- `find_log_file`
- `write_remote_file`
- `append_remote_file`

实验工具需要显式开启，演进速度也可能更快。只有在它们确实能减少排障试探成本时，才建议启用。

开启方式：

```powershell
agent-remote-bridge --experimental-tools
```

或者：

```powershell
$env:ARB_ENABLE_EXPERIMENTAL_TOOLS=1
```

## 安全模型

Agent Remote Bridge 是一个**受控远程执行桥**，不是沙箱。

当前保护边界包括：

- 按主机配置的 `allowed_paths`
- 命令风险分级
- 显式 `sudo` 策略
- session TTL 与 closed session 拒绝执行
- 带摘要、失败阶段、重试信息的本地审计记录

`exec_remote` 是有意保留的强能力入口，建议和策略、审计、评审一起使用。

安全报告和披露流程见 [SECURITY.md](./SECURITY.md)。

## 支持矩阵

### 本地运行环境

- Windows：支持
- macOS：支持
- Linux：支持
- Python: `3.11` and `3.12`

### 远程目标

- 仅支持 Linux
- 仅支持 SSH
- 仅支持非交互式命令执行

### 传输方式

- `stdio`
- `sse`
- `streamable-http`

## 仓库导航

- [QUICKSTART.md](./QUICKSTART.md)：5 分钟上手
- [CLIENTS.md](./CLIENTS.md)：客户端接入示例
- [CONTRIBUTING.md](./CONTRIBUTING.md)：开发流程与贡献规则
- [SUPPORT.md](./SUPPORT.md)：支持说明与提问建议
- [RELEASE.md](./RELEASE.md)：发布检查与打标签流程

## 路线图

当前阶段的重点是：

1. 完成这轮收口后冻结稳定工具契约
2. 维持 Windows、macOS、Linux 三端 CI 绿色
3. 提供可安装的发布产物
4. 保持文档、诊断命令和 release gate 一致

## 许可证

本项目基于 [MIT License](./LICENSE) 发布。
