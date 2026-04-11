from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ExecutionResult:
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int


class RemoteAdapter:
    def execute(self, host, remote_command: str, timeout_sec: int = 60) -> ExecutionResult:  # noqa: ANN001
        raise NotImplementedError
