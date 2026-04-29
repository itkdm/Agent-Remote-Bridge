from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppSettings:
    project_root: Path
    config_dir: Path
    data_dir: Path
    host_config_path: Path
    sqlite_path: Path
    enable_experimental_tools: bool
    session_ttl_hours: int


def load_settings() -> AppSettings:
    project_root = Path(__file__).resolve().parents[2]
    config_dir = project_root / "config"
    data_dir = project_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    sqlite_path = Path(os.environ.get("ARB_SQLITE_PATH", data_dir / "state.db"))
    if not sqlite_path.is_absolute():
        sqlite_path = project_root / sqlite_path
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    enable_experimental_tools = os.environ.get("ARB_ENABLE_EXPERIMENTAL_TOOLS", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    session_ttl_hours = int(os.environ.get("ARB_SESSION_TTL_HOURS", "24"))
    return AppSettings(
        project_root=project_root,
        config_dir=config_dir,
        data_dir=data_dir,
        host_config_path=config_dir / "hosts.yaml",
        sqlite_path=sqlite_path,
        enable_experimental_tools=enable_experimental_tools,
        session_ttl_hours=session_ttl_hours,
    )
