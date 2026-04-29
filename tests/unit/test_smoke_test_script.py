from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_smoke_test_module():
    module_path = Path(__file__).resolve().parents[2] / "scripts" / "smoke_test.py"
    spec = importlib.util.spec_from_file_location("arb_smoke_test", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_call_tool_reads_fastmcp_tuple_result() -> None:
    module = _load_smoke_test_module()

    class _Text:
        def __init__(self, text: str) -> None:
            self.text = text

    class _FakeServer:
        async def call_tool(self, name: str, arguments: dict):  # noqa: ANN001
            return ([_Text(json.dumps({"ok": True, "message": "done"}))], {"result": {"ok": True}})

    result = module.asyncio.run(module.call_tool(_FakeServer(), "list_hosts", {}))

    assert result["ok"] is True
    assert result["message"] == "done"
