# Support / 支持

## When to use GitHub Issues / 何时提 Issue

- Reproducible bugs
- Documentation gaps
- Client compatibility issues
- Feature requests that fit the roadmap

- 可稳定复现的 bug
- 文档缺失或表达不清
- MCP 客户端兼容性问题
- 符合当前路线图的功能建议

## Before Opening an Issue / 提交前先检查

- Read [README.md](./README.md)
- Try [QUICKSTART.md](./QUICKSTART.md)
- Review [CLIENTS.md](./CLIENTS.md)
- Run `python .\scripts\release_gate.py --dry-run`

如果问题涉及敏感安全细节，请不要直接提交公开 issue，改走 [SECURITY.md](./SECURITY.md) 中的流程。

## What Maintainers Need / 维护者需要的信息

- Local OS and Python version
- MCP client and transport
- Relevant `agent-remote-bridge` command or tool call
- Redacted logs or audit output
- Remote distro details when relevant

- 本地操作系统与 Python 版本
- MCP 客户端名称与 transport
- 相关的 `agent-remote-bridge` 命令或 tool 调用
- 脱敏后的日志或审计输出
- 需要时补充远程 Linux 发行版信息

## Maintainer Contact / 联系维护者

If you need a private maintainer contact path for conduct or support reasons, open a minimal public issue without sensitive details and ask for a private follow-up channel.

如果你因为行为准则或支持问题需要私下联系维护者，可以提交一个不包含敏感信息的最小公开 issue，请求转到私下沟通渠道。
