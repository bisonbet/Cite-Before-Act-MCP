"""Bot Framework adapter configuration for Microsoft Teams."""

import os
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings
from botbuilder.schema import Activity


def create_teams_adapter(app_id: str = None, app_password: str = None) -> BotFrameworkAdapter:
    """
    Create and configure a Bot Framework adapter for Teams.

    Args:
        app_id: Microsoft App ID (defaults to TEAMS_APP_ID env var)
        app_password: Microsoft App Password (defaults to TEAMS_APP_PASSWORD env var)

    Returns:
        Configured BotFrameworkAdapter

    Raises:
        ValueError: If app_id or app_password not provided
    """
    app_id = app_id or os.getenv("TEAMS_APP_ID")
    app_password = app_password or os.getenv("TEAMS_APP_PASSWORD")

    if not app_id or not app_password:
        raise ValueError(
            "Teams App ID and Password are required. "
            "Set TEAMS_APP_ID and TEAMS_APP_PASSWORD environment variables."
        )

    settings = BotFrameworkAdapterSettings(
        app_id=app_id,
        app_password=app_password,
    )

    adapter = BotFrameworkAdapter(settings)

    # Error handler
    async def on_error(context, error):
        print(f"❌ Teams bot error: {error}", flush=True)
        await context.send_activity("Sorry, an error occurred.")

    adapter.on_turn_error = on_error

    return adapter


def parse_teams_activity(request_body: dict) -> Activity:
    """
    Parse Teams request body into an Activity object.

    Args:
        request_body: Request body from Teams webhook

    Returns:
        Activity object
    """
    return Activity().deserialize(request_body)
