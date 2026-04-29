# Agent Remote Bridge

[中文 README](./README.md)

[![CI](https://github.com/itkdm/Agent-Remote-Bridge/actions/workflows/ci.yml/badge.svg)](https://github.com/itkdm/Agent-Remote-Bridge/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

Agent Remote Bridge is a controlled MCP server that lets a local coding agent work against a real remote Linux host over SSH.

Its role is intentionally narrow: keep local agent context intact while providing a more controlled path into real remote Linux environments.

The project is currently in the `0.2.x beta` stage: the core workflow is usable, but the public contract is still being tightened.

## What It Is

- Local-first: your MCP client runs locally, while the bridge reaches the remote host.
- Remote Linux only: the bridge targets real Linux environments, not local shell emulation.
- Non-interactive by design: sessions preserve context, but they are not persistent remote shells.
- Agent-oriented: it is built for MCP clients such as VS Code, Codex Desktop, Claude Desktop, and other agent runtimes.

## Why Not Plain SSH

Plain SSH is flexible, but it does not give an MCP agent stable tool contracts, structured diagnostics, bounded file operations, or local audit history.

Agent Remote Bridge adds:

- logical sessions with cwd and lightweight context retention
- structured tool responses with `error_type` and suggestions
- path allowlists and risk-aware execution boundaries
- local audit and diagnostic commands such as `doctor`, `preflight`, and `audit recent`

## Who Should Use It

Use Agent Remote Bridge if you:

- build or operate MCP-enabled coding agents
- want a local agent to inspect or change a remote Linux environment
- need more control than ad-hoc SSH hopping
- prefer a small, explicit tool surface over a heavy remote automation platform

Do **not** use it if you need:

- interactive TTY sessions
- non-Linux remote targets
- team RBAC or multi-tenant control planes
- Docker / Kubernetes / WinRM adapters today

## Quickstart

For now, the most reliable install path is still source-based:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv\Scripts\python.exe -m pip install -e .
```

Create a local host config:

```powershell
Copy-Item .\config\hosts.example.yaml .\config\hosts.yaml
```

If you use password auth, set the environment variable:

```powershell
$env:ARB_DEMO_SERVER_PASSWORD="YOUR_PASSWORD"
```

Validate before connecting:

```powershell
agent-remote-bridge config-validate
agent-remote-bridge preflight --host-id demo-server
```

Start the MCP server:

```powershell
agent-remote-bridge --transport stdio
```

After startup, try these first three actions:

1. `list_hosts`
2. `open_session(host_id="demo-server")`
3. `exec_remote(command="pwd")`

For a more guided first run, see [QUICKSTART.md](./QUICKSTART.md).

The tracked example config lives at [config/hosts.example.yaml](./config/hosts.example.yaml).

## Stable vs Experimental

### Stable tools

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

These tools make up the default public contract. Any behavior change should come with tests, documentation updates, and release notes.

### Experimental tools

- `test_host_connection`
- `tail_remote_logs`
- `check_port_listening`
- `inspect_processes`
- `find_log_file`
- `write_remote_file`
- `append_remote_file`

Experimental tools are opt-in and may evolve faster. Enable them only when they clearly reduce trial-and-error during diagnostics or controlled writes.

Enable them with:

```powershell
agent-remote-bridge --experimental-tools
```

or:

```powershell
$env:ARB_ENABLE_EXPERIMENTAL_TOOLS=1
```

## Security Model

Agent Remote Bridge is a **controlled remote execution bridge**, not a sandbox.

Current guardrails include:

- host-scoped `allowed_paths`
- command risk classification
- explicit `sudo` policy
- session TTL and closed-session rejection
- local audit records with summaries, failure stages, and retry metadata

`exec_remote` is intentionally powerful. Treat it as an escape hatch with policy, audit, and review around it.

See [SECURITY.md](./SECURITY.md) for disclosure guidance.

## Supported Platforms

### Local runtime

- Windows: supported
- macOS: supported
- Linux: supported
- Python: `3.11` and `3.12`

### Remote targets

- Linux only
- SSH only
- non-interactive command execution only

### Transports

- `stdio`
- `sse`
- `streamable-http`

## Repository Guide

- [QUICKSTART.md](./QUICKSTART.md): 5-minute setup
- [CLIENTS.md](./CLIENTS.md): client integration examples
- [CONTRIBUTING.md](./CONTRIBUTING.md): development workflow and contribution rules
- [SUPPORT.md](./SUPPORT.md): support guidance
- [RELEASE.md](./RELEASE.md): release checklist and tagging flow

## Roadmap

Current priorities:

1. Freeze the stable tool contract after this cleanup pass
2. Keep CI green across Windows, macOS, and Linux
3. Publish installable release artifacts
4. Keep docs, diagnostics, and release gates aligned

## License

This project is released under the [MIT License](./LICENSE).
