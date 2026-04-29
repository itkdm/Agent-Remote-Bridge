from __future__ import annotations

import subprocess
import time

import paramiko

from agent_remote_bridge.adapters.base import ExecutionResult, RemoteAdapter
from agent_remote_bridge.models import HostConfig
from agent_remote_bridge.utils.errors import (
    RemoteExecutionError,
    SSHAuthError,
    SSHBannerError,
    SSHConnectionError,
    TimeoutError,
)


class SSHAdapter(RemoteAdapter):
    _TRANSIENT_PARAMIKO_PATTERNS = (
        "error reading ssh protocol banner",
        "connection reset by peer",
        "connection reset",
        "connection aborted",
        "connection refused",
        "eoferror",
        "no existing session",
    )

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
        classified = self._classify_ssh_subprocess_failure(completed.stderr, completed.returncode)
        if classified is not None:
            self._attach_retry_metadata(classified, retry_count=0)
            raise classified
        return ExecutionResult(
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            duration_ms=duration_ms,
            retry_count=0,
            retried=False,
        )

    def _execute_with_paramiko(self, host: HostConfig, remote_command: str, timeout_sec: int) -> ExecutionResult:
        password = host.resolved_password()
        if not password:
            source = f"environment variable '{host.password_env}'" if host.password_env else "host config password"
            error = SSHAuthError(f"SSH authentication failed: missing password from {source}")
            self._attach_retry_metadata(error, retry_count=0)
            raise error

        started = time.perf_counter()
        max_attempts = 3
        last_error: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                client.connect(
                    hostname=host.host,
                    port=host.port,
                    username=host.username,
                    password=password,
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
                duration_ms = int((time.perf_counter() - started) * 1000)
                return ExecutionResult(
                    exit_code=exit_code,
                    stdout=stdout,
                    stderr=stderr,
                    duration_ms=duration_ms,
                    retry_count=attempt - 1,
                    retried=attempt > 1,
                )
            except TimeoutError:
                raise
            except Exception as exc:
                last_error = exc
                message = str(exc).lower()
                if "timed out" in message or "timeout" in message:
                    timeout_error = TimeoutError(f"Command timed out after {timeout_sec}s")
                    self._attach_retry_metadata(timeout_error, retry_count=attempt - 1)
                    raise timeout_error from exc
                if attempt < max_attempts and self._is_transient_paramiko_error(exc):
                    time.sleep(0.5 * attempt)
                    continue
                classified = self._classify_paramiko_error(exc)
                self._attach_retry_metadata(classified, retry_count=attempt - 1)
                raise classified from exc
            finally:
                client.close()

        classified = self._classify_paramiko_error(last_error)
        self._attach_retry_metadata(classified, retry_count=max_attempts - 1)
        raise classified

    def _is_transient_paramiko_error(self, exc: Exception) -> bool:
        message = str(exc).lower()
        return any(pattern in message for pattern in self._TRANSIENT_PARAMIKO_PATTERNS)

    def _classify_paramiko_error(self, exc: Exception | None) -> RemoteExecutionError:
        if exc is None:
            return RemoteExecutionError("SSH password connection failed: unknown error")

        message = str(exc)
        lowered = message.lower()

        if "authentication failed" in lowered or "auth failed" in lowered or "permission denied" in lowered:
            return SSHAuthError(f"SSH authentication failed: {message}")
        if "error reading ssh protocol banner" in lowered or "banner" in lowered or "no existing session" in lowered:
            return SSHBannerError(f"SSH banner error: {message}")
        if (
            "connection refused" in lowered
            or "connection reset" in lowered
            or "connection aborted" in lowered
            or "unable to connect" in lowered
            or "network is unreachable" in lowered
            or "no route to host" in lowered
            or "name or service not known" in lowered
            or "getaddrinfo failed" in lowered
            or "eoferror" in lowered
        ):
            return SSHConnectionError(f"SSH connection failed: {message}")
        return RemoteExecutionError(f"SSH password connection failed: {message}")

    def _classify_ssh_subprocess_failure(self, stderr: str, returncode: int) -> RemoteExecutionError | None:
        if returncode == 0:
            return None

        lowered = (stderr or "").lower()
        if "permission denied" in lowered or "authentication failed" in lowered:
            return SSHAuthError(f"SSH authentication failed: {stderr.strip() or 'unknown ssh auth failure'}")
        if "banner" in lowered:
            return SSHBannerError(f"SSH banner error: {stderr.strip() or 'unknown ssh banner failure'}")
        if (
            "connection refused" in lowered
            or "connection reset" in lowered
            or "connection aborted" in lowered
            or "could not resolve hostname" in lowered
            or "name or service not known" in lowered
            or "network is unreachable" in lowered
            or "no route to host" in lowered
            or "operation timed out" in lowered
        ):
            return SSHConnectionError(f"SSH connection failed: {stderr.strip() or 'unknown ssh connection failure'}")
        return None

    @staticmethod
    def _attach_retry_metadata(exc: Exception, *, retry_count: int) -> None:
        setattr(exc, "retry_count", max(retry_count, 0))
        setattr(exc, "retried", retry_count > 0)
