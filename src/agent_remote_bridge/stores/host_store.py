from __future__ import annotations

from collections import Counter
import os
from pathlib import Path
from typing import Any

import yaml

from agent_remote_bridge.models import HostConfig
from agent_remote_bridge.utils.errors import ConfigError, NotFoundError


class HostStore:
    def __init__(self, config_path: Path) -> None:
        self._config_path = config_path

    def list_hosts(self) -> list[HostConfig]:
        if not self._config_path.exists():
            return []
        payload = self._read_payload()
        hosts = payload.get("hosts", [])
        return [HostConfig.model_validate(item) for item in hosts]

    def _read_payload(self) -> dict[str, Any]:
        return yaml.safe_load(self._config_path.read_text(encoding="utf-8")) or {}

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

    def validate_config(self) -> dict[str, Any]:
        errors: list[str] = []
        warnings: list[str] = []
        hosts_summary: list[dict[str, Any]] = []

        if not self._config_path.exists():
            errors.append(
                f"Host config file not found: {self._config_path}. Copy config/hosts.example.yaml to config/hosts.yaml first."
            )
            return {
                "ok": False,
                "path": str(self._config_path),
                "errors": errors,
                "warnings": warnings,
                "host_count": 0,
                "hosts": hosts_summary,
            }

        try:
            payload = self._read_payload()
        except yaml.YAMLError as exc:
            errors.append(f"YAML parse failed: {exc}")
            return {
                "ok": False,
                "path": str(self._config_path),
                "errors": errors,
                "warnings": warnings,
                "host_count": 0,
                "hosts": hosts_summary,
            }

        raw_hosts = payload.get("hosts", [])
        if not isinstance(raw_hosts, list):
            errors.append("Top-level 'hosts' must be a list.")
            raw_hosts = []

        host_ids = [item.get("host_id") for item in raw_hosts if isinstance(item, dict) and item.get("host_id")]
        duplicate_ids = [host_id for host_id, count in Counter(host_ids).items() if count > 1]
        for host_id in duplicate_ids:
            errors.append(f"Duplicate host_id found: {host_id}")

        for index, item in enumerate(raw_hosts, start=1):
            if not isinstance(item, dict):
                errors.append(f"Host entry #{index} must be a mapping.")
                continue

            host_id = item.get("host_id") or f"<missing:{index}>"
            host_errors: list[str] = []
            host_warnings: list[str] = []

            try:
                host = HostConfig.model_validate(item)
            except Exception as exc:
                host_errors.append(f"Schema validation failed: {exc}")
                hosts_summary.append(
                    {
                        "host_id": host_id,
                        "ok": False,
                        "errors": host_errors,
                        "warnings": host_warnings,
                    }
                )
                continue

            if not host.default_workdir.strip():
                host_errors.append("default_workdir must not be empty.")
            elif not host.default_workdir.startswith("/"):
                host_errors.append("default_workdir must be an absolute path.")

            if not host.allowed_paths:
                host_errors.append("allowed_paths must not be empty.")
            else:
                for allowed_path in host.allowed_paths:
                    if not allowed_path.strip():
                        host_errors.append("allowed_paths must not contain empty entries.")
                    elif not allowed_path.startswith("/"):
                        host_errors.append(f"allowed_path must be an absolute path: {allowed_path}")

            if host.auth_mode == "password":
                if not host.username.strip():
                    host_errors.append("username is required for password auth.")
                if not ((host.password and host.password.strip()) or (host.password_env and host.password_env.strip())):
                    host_errors.append("password auth requires either password or password_env.")
                if host.password_env and not os.environ.get(host.password_env):
                    host_errors.append(f"password_env is set but environment variable is missing: {host.password_env}")
                if host.private_key_path:
                    host_warnings.append("private_key_path is ignored for password auth.")
                if host.ssh_config_host:
                    host_warnings.append("ssh_config_host is ignored for password auth.")
            elif host.auth_mode == "key_path":
                if not (host.private_key_path and host.private_key_path.strip()):
                    host_errors.append("private_key_path is required for key_path auth.")
                else:
                    key_path = Path(host.private_key_path).expanduser()
                    if not key_path.is_absolute():
                        host_warnings.append("private_key_path should be an absolute local path.")
                    if not key_path.exists():
                        host_errors.append(f"private_key_path does not exist on this machine: {key_path}")
                    elif not key_path.is_file():
                        host_errors.append(f"private_key_path is not a file: {key_path}")
                if host.password or host.password_env:
                    host_warnings.append("password and password_env are ignored for key_path auth.")
                if host.ssh_config_host:
                    host_warnings.append("ssh_config_host is ignored for key_path auth.")
            elif host.auth_mode == "ssh_config":
                if not (host.ssh_config_host and host.ssh_config_host.strip()):
                    host_errors.append("ssh_config_host is required for ssh_config auth.")
                if host.private_key_path:
                    host_warnings.append("private_key_path is ignored for ssh_config auth; configure the key in your SSH config.")
                if host.password or host.password_env:
                    host_warnings.append("password and password_env are ignored for ssh_config auth.")

            if host.allow_sudo and host.username != "root":
                host_warnings.append("allow_sudo is enabled for a non-root user; confirm sudo is configured.")

            if host.auth_mode == "password" and host.password:
                host_warnings.append("Plaintext password is stored in hosts.yaml; prefer password_env.")
            if host.auth_mode == "password" and host.password and host.password_env:
                host_warnings.append("password_env will take precedence over plaintext password.")
            if host.auth_mode == "key_path":
                host_warnings.append("SSH key auth is preferred for long-term use.")
            if host.auth_mode == "ssh_config":
                host_warnings.append("SSH config auth is preferred when you already manage hosts in ~/.ssh/config.")

            if host.host in {"YOUR_SERVER_IP", "CHANGE_ME", "example.com"}:
                host_warnings.append("Host still looks like a placeholder value.")

            if host.port <= 0 or host.port > 65535:
                host_errors.append(f"port is out of range: {host.port}")

            hosts_summary.append(
                {
                    "host_id": host.host_id,
                    "ok": len(host_errors) == 0,
                    "errors": host_errors,
                    "warnings": host_warnings,
                }
            )
            errors.extend(f"{host.host_id}: {message}" for message in host_errors)
            warnings.extend(f"{host.host_id}: {message}" for message in host_warnings)

        return {
            "ok": len(errors) == 0,
            "path": str(self._config_path),
            "errors": errors,
            "warnings": warnings,
            "host_count": len(raw_hosts),
            "hosts": hosts_summary,
        }
