from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_check_docs_module():
    module_path = Path(__file__).resolve().parents[2] / "scripts" / "check_docs.py"
    spec = importlib.util.spec_from_file_location("arb_check_docs", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_check_docs_only_requires_top_level_readme() -> None:
    module = _load_check_docs_module()

    assert [doc.name for doc in module.DOC_FILES] == ["README.md"]
