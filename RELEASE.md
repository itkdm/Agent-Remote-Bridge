# Release Guide / 发布指南

## Goals / 目标

Every release should be installable, documented, and reproducible.

每次发布都应满足：可安装、文档同步、可复现。

## Pre-release Checklist / 发布前检查

```powershell
python -m pytest
python .\scripts\check_docs.py
python -m build
python -m twine check dist/*
python .\scripts\release_gate.py --dry-run
```

If a safe remote host is available:

```powershell
python .\scripts\release_gate.py --host-id demo-server
```

## Versioning / 版本策略

- Use semantic versioning.
- `0.x` releases may still make controlled contract changes.
- Any public contract change must be reflected in `CHANGELOG.md`.

## Tagging / 打标签

```powershell
git tag v0.2.0
git push origin main --follow-tags
```

The release workflow builds artifacts, attaches them to the GitHub release, and publishes to PyPI when repository permissions are configured correctly.
