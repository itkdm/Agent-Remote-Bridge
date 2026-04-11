from __future__ import annotations

from pathlib import PurePosixPath


def resolve_remote_path(current_cwd: str, path: str) -> str:
    candidate = PurePosixPath(path)
    if candidate.is_absolute():
        return str(candidate)
    return str(PurePosixPath(current_cwd) / candidate)
