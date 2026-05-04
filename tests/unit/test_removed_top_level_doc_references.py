from __future__ import annotations

from pathlib import Path


REMOVED_DOC_NAMES = (
    "README.en.md",
    "QUICKSTART.md",
    "CLIENTS.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "SUPPORT.md",
    "RELEASE.md",
    "CHANGELOG.md",
    "CODE_OF_CONDUCT.md",
)

SKIP_DIR_NAMES = {".git", ".venv", "__pycache__", "agent_remote_bridge.egg-info"}
TEXT_SUFFIXES = {".md", ".py", ".toml", ".yml", ".yaml", ".txt"}


def test_repo_sources_do_not_reference_removed_top_level_docs() -> None:
    root = Path(__file__).resolve().parents[2]
    hits: list[str] = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        if path.suffix not in TEXT_SUFFIXES:
            continue
        if path == Path(__file__).resolve():
            continue

        content = path.read_text(encoding="utf-8")
        for doc_name in REMOVED_DOC_NAMES:
            if doc_name in content:
                hits.append(f"{path.relative_to(root)} -> {doc_name}")

    assert hits == []
