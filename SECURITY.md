# Security Policy / 安全策略

## Scope / 范围

Agent Remote Bridge is a controlled remote execution bridge, not a sandbox, privilege boundary, or zero-risk automation system.

Agent Remote Bridge 是一个受控远程执行桥，不是沙箱、权限边界，也不是零风险自动化系统。

## Supported Versions / 支持版本

- `0.2.x`: security fixes and contract clarifications
- Older `0.x` builds: no guaranteed security maintenance

## Reporting / 报告方式

Please do **not** post exploit details in public issues.

请不要在公开 issue 中直接披露利用细节。

Open a private security report through GitHub Security Advisories if the repository has it enabled. If that path is unavailable, open a minimal public issue requesting a private contact channel and reference this file without including exploit details.

## Response Goals / 响应目标

- Acknowledge initial reports within 5 business days
- Triage severity and affected versions
- Publish a fix and upgrade guidance when ready

## What to Report / 适合报告的问题

- Path allowlist bypasses
- Session lifecycle bypasses
- Unsafe file write behavior
- Authentication handling flaws
- Audit or disclosure leaks
