class BridgeError(Exception):
    """Base exception for the bridge."""

    error_type = "bridge_error"


class NotFoundError(BridgeError):
    error_type = "not_found"


class ConfigError(BridgeError):
    error_type = "config_error"


class SecurityError(BridgeError):
    error_type = "command_blocked"


class PathNotAllowedError(SecurityError):
    error_type = "path_not_allowed"


class RemoteExecutionError(BridgeError):
    error_type = "remote_execution_failed"


class TimeoutError(BridgeError):
    error_type = "command_timeout"


class SSHAuthError(RemoteExecutionError):
    error_type = "ssh_auth_failed"


class SSHBannerError(RemoteExecutionError):
    error_type = "ssh_banner_error"


class SSHConnectionError(RemoteExecutionError):
    error_type = "ssh_connection_error"


class SessionClosedError(BridgeError):
    error_type = "session_closed"


class SessionExpiredError(BridgeError):
    error_type = "session_expired"


class UnsupportedRemoteStateError(BridgeError):
    error_type = "unsupported_remote_state"
