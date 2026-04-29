from __future__ import annotations

import socket

from agent_remote_bridge.adapters.ssh_adapter import SSHAdapter
from agent_remote_bridge.models import HostConfig
from agent_remote_bridge.services.audit_service import AuditService
from agent_remote_bridge.utils.errors import BridgeError
from agent_remote_bridge.utils.suggested_actions import suggested_actions_for_error
from agent_remote_bridge.utils.truncation import truncate_text


class HostService:
    def __init__(self, *, adapter: SSHAdapter, audit_service: AuditService) -> None:
        self._adapter = adapter
        self._audit_service = audit_service

    def test_connection(self, host: HostConfig, timeout_sec: int = 15) -> dict:
        result = self._adapter.execute(host, "printf 'ok'", timeout_sec=timeout_sec)
        stdout, truncated = truncate_text(result.stdout, max_chars=200)
        stderr, _ = truncate_text(result.stderr, max_chars=400)
        ok = result.exit_code == 0 and stdout.strip() == "ok"
        summary = "SSH connection succeeded" if ok else "SSH connection failed"
        self._audit_service.record(
            host_id=host.host_id,
            tool_name="test_host_connection",
            command="printf 'ok'",
            exit_code=result.exit_code,
            summary=summary,
            error_type=None if ok else "remote_execution_failed",
        )
        return {
            "host_id": host.host_id,
            "ok": ok,
            "exit_code": result.exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "duration_ms": result.duration_ms,
            "summary": summary,
            "truncated": truncated,
            "error_type": None if ok else "remote_execution_failed",
            "suggested_next_actions": [] if ok else suggested_actions_for_error("remote_execution_failed"),
        }

    def preflight(self, host: HostConfig, timeout_sec: int = 15) -> dict:
        stages: list[dict] = []

        try:
            resolved = socket.getaddrinfo(host.host, host.port, type=socket.SOCK_STREAM)
            resolved_ips = sorted({item[4][0] for item in resolved})
            stages.append(
                {
                    "name": "dns",
                    "ok": True,
                    "detail": f"Resolved host to {', '.join(resolved_ips[:5])}",
                    "error_type": None,
                }
            )
        except OSError as exc:
            stages.append(
                {
                    "name": "dns",
                    "ok": False,
                    "detail": str(exc),
                    "error_type": "ssh_connection_error",
                }
            )
            return self._build_preflight_result(host, stages)

        try:
            with socket.create_connection((host.host, host.port), timeout=timeout_sec):
                pass
            stages.append(
                {
                    "name": "tcp",
                    "ok": True,
                    "detail": f"Connected to {host.host}:{host.port}",
                    "error_type": None,
                }
            )
        except OSError as exc:
            stages.append(
                {
                    "name": "tcp",
                    "ok": False,
                    "detail": str(exc),
                    "error_type": "ssh_connection_error",
                }
            )
            return self._build_preflight_result(host, stages)

        try:
            with socket.create_connection((host.host, host.port), timeout=timeout_sec) as sock:
                sock.settimeout(timeout_sec)
                banner = sock.recv(255).decode("utf-8", errors="replace").strip()
            if banner.startswith("SSH-"):
                stages.append(
                    {
                        "name": "banner",
                        "ok": True,
                        "detail": banner,
                        "error_type": None,
                    }
                )
            else:
                stages.append(
                    {
                        "name": "banner",
                        "ok": False,
                        "detail": banner or "No SSH banner received",
                        "error_type": "ssh_banner_error",
                    }
                )
                return self._build_preflight_result(host, stages)
        except OSError as exc:
            stages.append(
                {
                    "name": "banner",
                    "ok": False,
                    "detail": str(exc),
                    "error_type": "ssh_banner_error",
                }
            )
            return self._build_preflight_result(host, stages)

        try:
            auth_result = self.test_connection(host, timeout_sec=timeout_sec)
            stages.append(
                {
                    "name": "auth",
                    "ok": auth_result["ok"],
                    "detail": auth_result["summary"],
                    "error_type": None if auth_result["ok"] else auth_result.get("error_type", "remote_execution_failed"),
                }
            )
            return self._build_preflight_result(host, stages, auth_result=auth_result)
        except BridgeError as exc:
            stages.append(
                {
                    "name": "auth",
                    "ok": False,
                    "detail": str(exc),
                    "error_type": exc.error_type,
                }
            )
            return self._build_preflight_result(host, stages)

    def _build_preflight_result(
        self,
        host: HostConfig,
        stages: list[dict],
        *,
        auth_result: dict | None = None,
    ) -> dict:
        ok = all(stage["ok"] for stage in stages)
        failed_stage = next((stage for stage in stages if not stage["ok"]), None)
        summary = "Remote preflight succeeded" if ok else f"Remote preflight failed at {failed_stage['name']}"
        self._audit_service.record(
            host_id=host.host_id,
            tool_name="preflight",
            command=None,
            exit_code=0 if ok else 1,
            summary=summary,
            error_type=None if ok else failed_stage["error_type"],
            failure_stage=None if ok else failed_stage["name"],
        )
        return {
            "host_id": host.host_id,
            "ok": ok,
            "summary": summary,
            "stages": stages,
            "auth_result": auth_result,
        }
