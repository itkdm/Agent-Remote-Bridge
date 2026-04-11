from __future__ import annotations

import argparse
import os
from typing import Literal

from agent_remote_bridge.server import create_server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-remote-bridge",
        description="Agent Remote Bridge MCP server",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="MCP transport to serve. Default: stdio",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind host for HTTP-based transports. Default: 127.0.0.1",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Bind port for HTTP-based transports. Default: 8000",
    )
    parser.add_argument(
        "--sqlite-path",
        default=None,
        help="Override SQLite state path. Useful for tests or multiple local instances.",
    )
    parser.add_argument(
        "--experimental-tools",
        action="store_true",
        help="Expose experimental tools in addition to the stable tool set.",
    )
    parser.add_argument(
        "--log-level",
        default="ERROR",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Server log level. Default: ERROR",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.sqlite_path:
        os.environ["ARB_SQLITE_PATH"] = args.sqlite_path
    if args.experimental_tools:
        os.environ["ARB_ENABLE_EXPERIMENTAL_TOOLS"] = "1"

    server = create_server(
        host=args.host,
        port=args.port,
        log_level=args.log_level,
    )
    server.run(transport=args.transport)


if __name__ == "__main__":
    main()
