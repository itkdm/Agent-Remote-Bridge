from __future__ import annotations

import pytest

from agent_remote_bridge.utils.errors import SecurityError
from agent_remote_bridge.utils.remote_path import normalize_remote_path, resolve_remote_path


def test_resolve_remote_path_normalizes_relative_segments() -> None:
    resolved = resolve_remote_path("/srv/app/releases/current", "../shared/config.yaml")

    assert resolved == "/srv/app/releases/shared/config.yaml"


def test_resolve_remote_path_rejects_relative_escape_above_root() -> None:
    with pytest.raises(SecurityError):
        resolve_remote_path("/srv/app", "../../../etc/passwd")


def test_normalize_remote_path_rejects_non_absolute_paths() -> None:
    with pytest.raises(SecurityError):
        normalize_remote_path("var/log/app.log")
