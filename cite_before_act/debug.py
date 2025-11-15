"""Debug logging utility for Cite-Before-Act MCP."""

import os
import sys
from typing import Any


def is_debug_enabled() -> bool:
    """Check if debug logging is enabled.
    
    Returns:
        True if DEBUG environment variable is set to 'true' or '1'
    """
    debug_env = os.getenv("DEBUG", "").lower()
    return debug_env in ("true", "1", "yes", "on")


def debug_log(message: str, *args: Any) -> None:
    """Log a debug message if debug mode is enabled.
    
    Args:
        message: Debug message (can contain {} placeholders for formatting)
        *args: Positional arguments for message formatting using .format()
    """
    if is_debug_enabled():
        if args:
            try:
                formatted_message = message.format(*args)
            except (IndexError, KeyError):
                # If formatting fails, just append args
                formatted_message = f"{message} {args}"
        else:
            formatted_message = message
        print(f"[DEBUG] {formatted_message}", file=sys.stderr, flush=True)

