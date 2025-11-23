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

    # Configure BotFrameworkAdapterSettings with tenant-specific authentication
    # The auth_tenant_id parameter ensures authentication goes to the correct tenant
    # instead of defaulting to the "Bot Framework" tenant (which doesn't exist)
    settings_kwargs = {
        "app_id": app_id,
        "app_password": app_password,
    }
    
    # Store tenant credentials for fallback injection if needed
    tenant_credentials = None
    
    # Add tenant ID if provided - this is the proper way to configure tenant-specific auth
    if tenant_id:
        # Check if BotFrameworkAdapterSettings supports auth_tenant_id parameter
        # This is the recommended way to configure tenant-specific authentication
        try:
            import inspect
            settings_sig = inspect.signature(BotFrameworkAdapterSettings.__init__)
            if 'auth_tenant_id' in settings_sig.parameters:
                settings_kwargs["auth_tenant_id"] = tenant_id
                print(
                    f"✅ Teams adapter configured for tenant: {tenant_id}",
                    file=os.sys.stderr,
                )
            else:
                # Fallback: try alternative parameter names
                if 'tenant_id' in settings_sig.parameters:
                    settings_kwargs["tenant_id"] = tenant_id
                    print(
                        f"✅ Teams adapter configured for tenant: {tenant_id}",
                        file=os.sys.stderr,
                    )
                else:
                    # If auth_tenant_id is not supported, create tenant-specific credentials
                    # We'll inject them into the adapter after it's created
                    print(
                        f"⚠️ Warning: BotFrameworkAdapterSettings doesn't support auth_tenant_id. "
                        f"Using fallback credential configuration.",
                        file=os.sys.stderr,
                    )
                    if MicrosoftAppCredentials:
                        # Create tenant-specific credentials as fallback
                        # The authority should be just the base URL, not the full token endpoint
                        tenant_authority = f"https://login.microsoftonline.com/{tenant_id}"
                        # MicrosoftAppCredentials only accepts app_id and password
                        tenant_credentials = MicrosoftAppCredentials(
                            app_id=app_id,
                            password=app_password,
                        )
                        
                        # Set authority first - this is the key configuration
                        # The SDK will construct the OAuth endpoint from the authority
                        authority_set = False
                        if hasattr(tenant_credentials, 'authority'):
                            tenant_credentials.authority = tenant_authority
                            authority_set = True
                            print(
                                f"   ✓ Set authority: {tenant_authority}",
                                file=os.sys.stderr,
                            )
                        
                        # Only set OAuth endpoint if authority wasn't available
                        # If authority is set, the SDK should construct the endpoint automatically
                        if not authority_set:
                            oauth_endpoint = f"{tenant_authority}/oauth2/v2.0/token"
                            if hasattr(tenant_credentials, 'o_auth_endpoint'):
                                tenant_credentials.o_auth_endpoint = oauth_endpoint
                                print(
                                    f"   ✓ Set o_auth_endpoint: {oauth_endpoint}",
                                    file=os.sys.stderr,
                                )
                            elif hasattr(tenant_credentials, 'oauth_endpoint'):
                                tenant_credentials.oauth_endpoint = oauth_endpoint
                                print(
                                    f"   ✓ Set oauth_endpoint: {oauth_endpoint}",
                                    file=os.sys.stderr,
                                )
                            else:
                                print(
                                    f"   ⚠️ Warning: Could not set authority or OAuth endpoint",
                                    file=os.sys.stderr,
                                )
                        
                        # Set OAuth scope if the attribute exists
                        if hasattr(tenant_credentials, 'o_auth_scope'):
                            tenant_credentials.o_auth_scope = "https://api.botframework.com/.default"
                            print(
                                f"   ✓ Set o_auth_scope: https://api.botframework.com/.default",
                                file=os.sys.stderr,
                            )
                        elif hasattr(tenant_credentials, 'oauth_scope'):
                            tenant_credentials.oauth_scope = "https://api.botframework.com/.default"
                            print(
                                f"   ✓ Set oauth_scope: https://api.botframework.com/.default",
                                file=os.sys.stderr,
                            )
                        
                        print(
                            f"✅ Created tenant-specific credentials for tenant: {tenant_id}",
                            file=os.sys.stderr,
                        )
        except Exception as e:
            print(
                f"⚠️ Warning: Could not configure tenant-specific authentication: {e}",
                file=os.sys.stderr,
            )

    settings = BotFrameworkAdapterSettings(**settings_kwargs)
    adapter = BotFrameworkAdapter(settings)
    
    # If we created tenant-specific credentials as fallback, inject them into the adapter
    if tenant_credentials:
        try:
            # Try multiple ways to inject credentials into the adapter
            if hasattr(adapter, '_credentials'):
                adapter._credentials = tenant_credentials
            elif hasattr(adapter, 'credentials'):
                adapter.credentials = tenant_credentials
            elif hasattr(adapter.settings, 'credentials'):
                adapter.settings.credentials = tenant_credentials
            print(
                f"✅ Injected tenant-specific credentials into adapter",
                file=os.sys.stderr,
            )
        except Exception as e:
            print(
                f"⚠️ Warning: Could not inject tenant-specific credentials: {e}",
                file=os.sys.stderr,
            )

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
