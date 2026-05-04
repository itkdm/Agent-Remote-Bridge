from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC_FILES = [
    ROOT / "README.md",
]
LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def main() -> int:
    missing: list[str] = []
    for doc in DOC_FILES:
        if not doc.exists():
            missing.append(f"missing required doc: {doc.relative_to(ROOT)}")
            continue
        content = doc.read_text(encoding="utf-8")
        for match in LINK_PATTERN.finditer(content):
            target = match.group(1).strip()
            if not target or "://" in target or target.startswith("#") or target.startswith("mailto:"):
                continue
            normalized = target.split("#", 1)[0]
            resolved = (doc.parent / normalized).resolve()
            if not resolved.exists():
                missing.append(f"broken link in {doc.relative_to(ROOT)} -> {target}")

    if missing:
        for item in missing:
            print(item)
        return 1

    print("documentation checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
