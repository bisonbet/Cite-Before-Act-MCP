"""Bot Framework adapter configuration for Microsoft Teams."""

import os
from typing import Optional
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings
from botbuilder.schema import Activity

# Try to import MicrosoftAppCredentials for tenant-specific configuration
try:
    from botframework.connector.auth import MicrosoftAppCredentials
except ImportError:
    MicrosoftAppCredentials = None


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

    settings = BotFrameworkAdapterSettings(
        app_id=app_id,
        app_password=app_password,
    )

    # Store tenant-specific credentials if we create them
    tenant_credentials = None

    # Configure tenant-specific authentication if tenant_id is provided
    # This ensures authentication requests go to the correct tenant instead of
    # defaulting to the "Bot Framework" tenant (which doesn't exist)
    if tenant_id and MicrosoftAppCredentials:
        try:
            # Create tenant-specific credentials that will be used by the adapter
            # The adapter uses MicrosoftAppCredentials internally for token requests
            tenant_authority = f"https://login.microsoftonline.com/{tenant_id}"
            
            # Create credentials with tenant-specific OAuth endpoint
            tenant_credentials = MicrosoftAppCredentials(
                app_id=app_id,
                password=app_password,
                o_auth_scope="https://api.botframework.com/.default",
            )
            # Store for later use
            
            # Set the tenant-specific OAuth endpoint
            # This is the key fix: ensures authentication goes to your tenant, not "Bot Framework"
            if hasattr(tenant_credentials, 'o_auth_endpoint'):
                tenant_credentials.o_auth_endpoint = f"{tenant_authority}/oauth2/v2.0/token"
            elif hasattr(tenant_credentials, 'oauth_endpoint'):
                tenant_credentials.oauth_endpoint = f"{tenant_authority}/oauth2/v2.0/token"
            
            # Also try to set the authority directly if available
            if hasattr(tenant_credentials, 'authority'):
                tenant_credentials.authority = tenant_authority
            
            # Override the adapter's settings credentials if possible
            # Some SDK versions allow this, others create credentials internally
            if hasattr(settings, 'credentials'):
                settings.credentials = tenant_credentials
            
            print(
                f"✅ Teams adapter configured for tenant: {tenant_id}",
                file=os.sys.stderr,
            )
        except Exception as e:
            # If configuration fails, log a warning but continue
            # The tenant_id will still be used in conversation references
            print(
                f"⚠️ Warning: Could not configure tenant-specific authentication for {tenant_id}: {e}. "
                f"Authentication may fail. Ensure TEAMS_TENANT_ID is set correctly.",
                file=os.sys.stderr,
            )
    elif tenant_id:
        print(
            f"⚠️ Warning: Tenant ID provided but MicrosoftAppCredentials not available. "
            f"Install botframework-connector package for tenant-specific authentication.",
            file=os.sys.stderr,
        )

    adapter = BotFrameworkAdapter(settings)
    
    # If we created tenant-specific credentials, try to inject them into the adapter
    # The adapter may have already created credentials, so we try to override them
    if tenant_credentials:
        try:
            # Try to access and override the adapter's internal credentials
            # This is SDK-version dependent, so we try multiple approaches
            if hasattr(adapter, '_credentials'):
                adapter._credentials = tenant_credentials
            elif hasattr(adapter, 'credentials'):
                adapter.credentials = tenant_credentials
            elif hasattr(adapter.settings, 'credentials'):
                adapter.settings.credentials = tenant_credentials
        except Exception:
            # If we can't override, the settings-based approach above should work
            pass

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
