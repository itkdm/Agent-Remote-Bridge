from __future__ import annotations

import os
from typing import Literal

from pydantic import BaseModel, Field


class HostConfig(BaseModel):
    host_id: str
    alias: str | None = None
    host: str
    port: int = 22
    username: str
    auth_mode: Literal["ssh_config", "key_path", "direct", "password"] = "ssh_config"
    ssh_config_host: str | None = None
    private_key_path: str | None = None
    password: str | None = None
    password_env: str | None = None
    default_workdir: str = "/tmp"
    allowed_paths: list[str] = Field(default_factory=list)
    allow_sudo: bool = False
    tags: list[str] = Field(default_factory=list)

    def resolved_password(self) -> str | None:
        if self.password_env:
            return os.environ.get(self.password_env)
        return self.password
