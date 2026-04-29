# Contributing / 参与贡献

## Overview / 概览

Agent Remote Bridge welcomes bug reports, documentation improvements, compatibility fixes, and carefully scoped feature work.

Agent Remote Bridge 欢迎 bug 报告、文档改进、兼容性修复，以及边界清晰的功能增强。

## Project Rules / 项目规则

- Stable tools must remain predictable and documented.
- Experimental tools may evolve faster, but they still need tests and docs.
- Remote Linux only, SSH only, non-interactive execution only.
- Do not expand scope into shells, RBAC, or unrelated platform support without an agreed roadmap item.

## Development Setup / 本地开发

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## Validation / 验证

Run these before opening a PR:

```powershell
python -m pytest
python .\scripts\check_docs.py
python -m build
python -m twine check dist/*
python .\scripts\release_gate.py --dry-run
```

If you have a safe test host configured, also run:

```powershell
python .\scripts\release_gate.py --host-id demo-server
```

## Stable vs Experimental / 稳定与实验能力

- Stable tools are part of the public contract and require migration notes for behavior changes.
- Experimental tools are opt-in and may change faster, but any externally visible change still needs documentation.
- When in doubt, prefer moving risky capabilities to experimental instead of expanding the default stable surface.

## Pull Requests / 提交 PR

- Keep changes focused and atomic.
- Add or update tests first for behavior changes.
- Update README, QUICKSTART, CLIENTS, or other public docs when user-visible behavior changes.
- Update [CHANGELOG.md](./CHANGELOG.md) for notable changes.

## Design Boundaries / 设计边界

When adding a new tool, document:

- why it should exist instead of using `exec_remote`
- whether it belongs in stable or experimental
- what the security and audit expectations are
- how users should validate it locally
