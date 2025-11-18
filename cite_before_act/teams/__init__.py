"""Microsoft Teams integration for approval requests."""

from .client import TeamsClient
from .handlers import TeamsHandler
from .adapter import create_teams_adapter, parse_teams_activity

__all__ = [
    "TeamsClient",
    "TeamsHandler",
    "create_teams_adapter",
    "parse_teams_activity",
]
