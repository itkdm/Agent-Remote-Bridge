from __future__ import annotations


def suggested_actions_for_error(error_type: str) -> list[str]:
    if error_type == "ssh_auth_failed":
        return [
            "check username, password, or SSH key configuration",
            "confirm password login is still allowed on the remote host",
        ]
    if error_type == "ssh_banner_error":
        return [
            "retry after a short delay",
            "check whether the remote SSH service is overloaded or restarting",
        ]
    if error_type == "ssh_connection_error":
        return [
            "check whether port 22 is reachable from this machine",
            "check firewall, security group, or network routing rules",
        ]
    if error_type == "command_timeout":
        return [
            "retry with a larger timeout",
            "check whether the remote command is blocked or waiting for input",
        ]
    if error_type == "config_error":
        return [
            "copy config/hosts.example.yaml to config/hosts.yaml",
            "review the local host configuration file",
        ]
    if error_type == "not_found":
        return [
            "check the requested host_id, session_id, or path",
            "list available hosts or reopen the session",
        ]
    if error_type == "command_blocked":
        return [
            "narrow the command scope",
            "review the host security policy and allowed paths",
        ]
    return [
        "inspect the error message",
        "retry the action or review local and remote configuration",
    ]
