"""Bot Framework adapter configuration for Microsoft Teams."""

import os
from typing import Optional
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings
from botbuilder.schema import Activity


def create_teams_adapter(
    app_id: str = None,
    app_password: str = None,
    tenant_id: Optional[str] = None,
) -> BotFrameworkAdapter:
    """
    Create and configure a Bot Framework adapter for Teams.

    Args:
        app_id: Microsoft App ID (defaults to TEAMS_APP_ID env var)
        app_password: Microsoft App Password (defaults to TEAMS_APP_PASSWORD env var)
        tenant_id: Optional Azure AD Tenant ID for single-tenant authentication
                   (defaults to TEAMS_TENANT_ID env var)

    Returns:
        Configured BotFrameworkAdapter

    Raises:
        ValueError: If app_id or app_password not provided
    """
    app_id = app_id or os.getenv("TEAMS_APP_ID")
    app_password = app_password or os.getenv("TEAMS_APP_PASSWORD")
    tenant_id = tenant_id or os.getenv("TEAMS_TENANT_ID")

    if not app_id or not app_password:
        raise ValueError(
            "Teams App ID and Password are required. "
            "Set TEAMS_APP_ID and TEAMS_APP_PASSWORD environment variables."
        )
    
    # Debug: Verify credentials are loaded (don't print password)
    if app_id:
        print(
            f"📋 Teams App ID loaded: {app_id[:8]}... (from {'parameter' if app_id != os.getenv('TEAMS_APP_ID') else 'env'})",
            file=os.sys.stderr,
        )
    if app_password:
        print(
            f"📋 Teams App Password loaded: {'*' * min(len(app_password), 20)}... (from {'parameter' if app_password != os.getenv('TEAMS_APP_PASSWORD') else 'env'})",
            file=os.sys.stderr,
        )
    if tenant_id:
        print(
            f"📋 Teams Tenant ID loaded: {tenant_id}",
            file=os.sys.stderr,
        )
    else:
        print(
            "⚠️ Warning: TEAMS_TENANT_ID not set. Authentication may fail.",
            file=os.sys.stderr,
        )

    # Configure tenant-specific authentication
    # For Bot Framework SDK, we use channel_auth_tenant in settings
    if tenant_id:
        # Create settings with tenant-specific configuration
        # The channel_auth_tenant tells the adapter which tenant to authenticate against
        settings = BotFrameworkAdapterSettings(
            app_id=app_id,
            app_password=app_password,
            channel_auth_tenant=tenant_id,
        )

        # Create adapter with settings
        adapter = BotFrameworkAdapter(settings)

        print(
            f"✅ Teams adapter configured for tenant: {tenant_id}",
            file=os.sys.stderr,
        )
        print(
            f"   Using channel_auth_tenant for tenant-specific authentication",
            file=os.sys.stderr,
        )
    else:
        # No tenant ID - use default configuration
        # This may work for multi-tenant bots or if tenant is auto-detected
        print(
            f"⚠️ Warning: TEAMS_TENANT_ID not set. Using default authentication.",
            file=os.sys.stderr,
        )
        print(
            f"   For single-tenant bots, set TEAMS_TENANT_ID to avoid authentication errors.",
            file=os.sys.stderr,
        )

        settings = BotFrameworkAdapterSettings(
            app_id=app_id,
            app_password=app_password,
        )
        adapter = BotFrameworkAdapter(settings)

    # Error handler with more detailed error information
    async def on_error(context, error):
        error_msg = str(error)
        print(f"❌ Teams bot error: {error_msg}", flush=True)
        
        # Provide more specific guidance for common errors
        if "Unauthorized" in error_msg or "401" in error_msg:
            print(
                "💡 Troubleshooting 'Unauthorized' error:\n"
                "  1. Verify TEAMS_APP_ID and TEAMS_APP_PASSWORD are correct\n"
                "  2. Check that TEAMS_TENANT_ID matches your Azure AD tenant\n"
                "  3. Ensure the app secret hasn't expired in Azure Portal\n"
                "  4. Verify the app is registered in the correct tenant\n"
                "  5. Check that API permissions are granted with admin consent",
                file=os.sys.stderr,
                flush=True,
            )
        
        try:
            await context.send_activity("Sorry, an error occurred.")
        except Exception:
            # If we can't send a message, that's okay - we've already logged the error
            pass

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
