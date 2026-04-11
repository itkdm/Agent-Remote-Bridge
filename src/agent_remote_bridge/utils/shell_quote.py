from __future__ import annotations

import shlex


def quote(value: str) -> str:
    return shlex.quote(value)
