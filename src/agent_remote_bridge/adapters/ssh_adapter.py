from __future__ import annotations

import subprocess
import time

import paramiko

from agent_remote_bridge.adapters.base import ExecutionResult, RemoteAdapter
from agent_remote_bridge.models import HostConfig
from agent_remote_bridge.utils.errors import RemoteExecutionError, TimeoutError


class SSHAdapter(RemoteAdapter):
    def execute(self, host: HostConfig, remote_command: str, timeout_sec: int = 60) -> ExecutionResult:
        if host.auth_mode == "password":
            return self._execute_with_paramiko(host, remote_command, timeout_sec)

        target = host.ssh_config_host or f"{host.username}@{host.host}"
        command = ["ssh"]
        if host.auth_mode == "key_path" and host.private_key_path:
            command.extend(["-i", host.private_key_path])
        if host.port:
            command.extend(["-p", str(host.port)])
        command.extend([target, "--", remote_command])

        started = time.perf_counter()
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=timeout_sec,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(f"Command timed out after {timeout_sec}s") from exc
        except OSError as exc:
            raise RemoteExecutionError(f"Failed to invoke ssh: {exc}") from exc

        duration_ms = int((time.perf_counter() - started) * 1000)
        return ExecutionResult(
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            duration_ms=duration_ms,
        )

    def _execute_with_paramiko(self, host: HostConfig, remote_command: str, timeout_sec: int) -> ExecutionResult:
        if not host.password:
            raise RemoteExecutionError(f"Host '{host.host_id}' is missing password for password auth")

        started = time.perf_counter()
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                hostname=host.host,
                port=host.port,
                username=host.username,
                password=host.password,
                timeout=timeout_sec,
                banner_timeout=timeout_sec,
                auth_timeout=timeout_sec,
                look_for_keys=False,
                allow_agent=False,
            )
            _, stdout_stream, stderr_stream = client.exec_command(remote_command, timeout=timeout_sec)
            exit_code = stdout_stream.channel.recv_exit_status()
            stdout = stdout_stream.read().decode("utf-8", errors="replace")
            stderr = stderr_stream.read().decode("utf-8", errors="replace")
        except TimeoutError:
            raise
        except Exception as exc:
            message = str(exc).lower()
            if "timed out" in message or "timeout" in message:
                raise TimeoutError(f"Command timed out after {timeout_sec}s") from exc
            raise RemoteExecutionError(f"SSH password connection failed: {exc}") from exc
        finally:
            client.close()

        duration_ms = int((time.perf_counter() - started) * 1000)
        return ExecutionResult(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
        )
