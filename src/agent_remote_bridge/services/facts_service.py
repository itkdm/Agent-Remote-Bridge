from __future__ import annotations

from agent_remote_bridge.adapters.ssh_adapter import SSHAdapter
from agent_remote_bridge.models import HostConfig
from agent_remote_bridge.utils.truncation import truncate_text


class FactsService:
    def __init__(self, adapter: SSHAdapter) -> None:
        self._adapter = adapter

    def get_system_facts(self, host: HostConfig, timeout_sec: int = 30) -> dict:
        remote_script = """
OS_NAME=unknown
if [ -f /etc/os-release ]; then
  OS_NAME="$(awk -F= '/^PRETTY_NAME=/{gsub(/"/,"",$2); print $2; exit}' /etc/os-release)"
fi
if [ -z "$OS_NAME" ]; then
  OS_NAME=unknown
fi
KERNEL="$(cat /proc/sys/kernel/osrelease 2>/dev/null || echo unknown)"
ARCH="$(arch 2>/dev/null || echo unknown)"
PACKAGE_MANAGER=unknown
for candidate in dnf yum apt apk pacman zypper; do
  if command -v "$candidate" >/dev/null 2>&1; then
    PACKAGE_MANAGER="$candidate"
    break
  fi
done
SERVICE_MANAGER=unknown
if command -v systemctl >/dev/null 2>&1; then
  SERVICE_MANAGER=systemd
elif command -v service >/dev/null 2>&1; then
  SERVICE_MANAGER=service
fi
DOCKER_AVAILABLE=false
if command -v docker >/dev/null 2>&1; then
  DOCKER_AVAILABLE=true
fi
INSTALLED_TOOLS=''
for tool in git docker node python3 python; do
  if command -v "$tool" >/dev/null 2>&1; then
    if [ -n "$INSTALLED_TOOLS" ]; then
      INSTALLED_TOOLS="$INSTALLED_TOOLS,$tool"
    else
      INSTALLED_TOOLS="$tool"
    fi
  fi
done
printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
  "$OS_NAME" \
  "$KERNEL" \
  "$ARCH" \
  "${SHELL:-unknown}" \
  "$(hostname 2>/dev/null || echo unknown)" \
  "$PACKAGE_MANAGER" \
  "$SERVICE_MANAGER" \
  "$DOCKER_AVAILABLE"
printf '%s\n' "$INSTALLED_TOOLS"
""".strip()
        result = self._adapter.execute(host, remote_script, timeout_sec=timeout_sec)
        if result.exit_code != 0:
            stderr, _ = truncate_text(result.stderr, max_chars=1000)
            return {
                "os": "unknown",
                "kernel": "unknown",
                "arch": "unknown",
                "package_manager": "unknown",
                "service_manager": "unknown",
                "shell": "unknown",
                "docker_available": False,
                "installed_tools": [],
                "hostname": "unknown",
                "summary": "Failed to collect system facts",
                "raw_error": stderr.strip(),
            }
        parsed = {
            "os": "unknown",
            "kernel": "unknown",
            "arch": "unknown",
            "package_manager": "unknown",
            "service_manager": "unknown",
            "shell": "unknown",
            "docker_available": False,
            "installed_tools": [],
            "hostname": "unknown",
        }
        lines = result.stdout.splitlines()
        if lines:
            metadata = lines[0].split("\t")
            if len(metadata) == 8:
                (
                    parsed["os"],
                    parsed["kernel"],
                    parsed["arch"],
                    parsed["shell"],
                    parsed["hostname"],
                    parsed["package_manager"],
                    parsed["service_manager"],
                    docker_value,
                ) = metadata
                parsed["docker_available"] = docker_value.lower() == "true"
        if len(lines) > 1:
            parsed["installed_tools"] = [item for item in lines[1].split(",") if item]
        parsed["summary"] = (
            f"{parsed['os']} {parsed['kernel']} {parsed['arch']} "
            f"pkg={parsed['package_manager']} svc={parsed['service_manager']}"
        )
        return parsed

    def detect_os_label(self, host: HostConfig, timeout_sec: int = 15) -> str | None:
        command = "python3 - <<'PY'\nimport platform\nprint(platform.platform())\nPY"
        result = self._adapter.execute(host, command, timeout_sec=timeout_sec)
        if result.exit_code != 0:
            return None
        return result.stdout.strip() or None
