from __future__ import annotations

from pathlib import PurePosixPath

from agent_remote_bridge.utils.errors import SecurityError


def normalize_remote_path(path: str) -> str:
    candidate = PurePosixPath(path)
    if not candidate.is_absolute():
        raise SecurityError("Remote paths must resolve to an absolute path")

    normalized_parts: list[str] = []
    for part in candidate.parts:
        if part in {"", "/"}:
            continue
        if part == ".":
            continue
        if part == "..":
            if not normalized_parts:
                raise SecurityError("Remote path escapes above the filesystem root")
            normalized_parts.pop()
            continue
        normalized_parts.append(part)

    return "/" + "/".join(normalized_parts)


def resolve_remote_path(current_cwd: str, path: str) -> str:
    candidate = PurePosixPath(path)
    if candidate.is_absolute():
        return normalize_remote_path(str(candidate))
    return normalize_remote_path(str(PurePosixPath(current_cwd) / candidate))
