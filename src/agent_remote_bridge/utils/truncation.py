from __future__ import annotations


def truncate_text(text: str, max_chars: int = 8000) -> tuple[str, bool]:
    if len(text) <= max_chars:
        return text, False
    return text[: max_chars - 14] + "\n...[truncated]", True
