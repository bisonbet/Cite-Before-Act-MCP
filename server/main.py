"""Main entry point for the Cite-Before-Act MCP proxy server."""

import argparse
import sys
from pathlib import Path

from config.settings import Settings, get_settings, set_settings
from server.proxy import ProxyServer


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Cite-Before-Act MCP Proxy Server - Requires approval for mutating tool calls"
    )

    # Transport options
    parser.add_argument(
        "--transport",
        choices=["stdio", "http", "sse"],
        default="stdio",
        help="Transport type (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host for HTTP/SSE transport (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for HTTP/SSE transport (default: 8000)",
    )

    # Configuration file
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to configuration file (not yet implemented)",
    )

    # Environment file
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(".env"),
        help="Path to .env file (default: .env)",
    )

    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    # Load settings
    try:
        settings = get_settings()
    except Exception as e:
        print(f"Error loading settings: {e}", file=sys.stderr)
        sys.exit(1)

    # Validate required settings
    if not settings.upstream:
        print(
            "Error: Upstream server configuration required. Set UPSTREAM_COMMAND or UPSTREAM_URL.",
            file=sys.stderr,
        )
        sys.exit(1)

    if settings.enable_slack and not settings.slack:
        print(
            "Warning: Slack enabled but not configured. Set SLACK_BOT_TOKEN.",
            file=sys.stderr,
        )

    if settings.enable_webex and not settings.webex:
        print(
            "Warning: Webex enabled but not configured. Set WEBEX_BOT_TOKEN and WEBEX_ROOM_ID or WEBEX_PERSON_EMAIL.",
            file=sys.stderr,
        )

    if settings.enable_teams and not settings.teams:
        print(
            "Warning: Teams enabled but not configured. Set TEAMS_APP_ID and TEAMS_APP_PASSWORD.",
            file=sys.stderr,
        )

    # Create and run proxy server
    try:
        proxy = ProxyServer(settings)
        proxy.run(
            transport=args.transport,
            host=args.host,
            port=args.port,
        )
    except KeyboardInterrupt:
        print("\nShutting down...", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"Error running server: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

