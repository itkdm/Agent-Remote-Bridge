from __future__ import annotations

from pathlib import Path

import yaml

from agent_remote_bridge.models import HostConfig
from agent_remote_bridge.utils.errors import ConfigError, NotFoundError


class HostStore:
    def __init__(self, config_path: Path) -> None:
        self._config_path = config_path

    def list_hosts(self) -> list[HostConfig]:
        if not self._config_path.exists():
            return []
        payload = yaml.safe_load(self._config_path.read_text(encoding="utf-8")) or {}
        hosts = payload.get("hosts", [])
        return [HostConfig.model_validate(item) for item in hosts]

    def get_host(self, host_id: str) -> HostConfig:
        for host in self.list_hosts():
            if host.host_id == host_id:
                return host
        raise NotFoundError(f"Host '{host_id}' not found in {self._config_path}")

    def ensure_config_exists(self) -> None:
        if not self._config_path.exists():
            raise ConfigError(
                f"Host config file not found: {self._config_path}. "
                "Copy config/hosts.example.yaml to config/hosts.yaml first."
            )
