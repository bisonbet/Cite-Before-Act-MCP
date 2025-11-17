"""Example: Using Cite-Before-Act as a library."""

import asyncio
from cite_before_act import DetectionEngine, ExplainEngine, ApprovalManager, Middleware
from cite_before_act.local_approval import LocalApproval
from cite_before_act.slack import SlackClient, SlackHandler


async def example_tool_call(tool_name: str, arguments: dict) -> dict:
    """Example upstream tool call function.

    Args:
        tool_name: Name of the tool
        arguments: Arguments to pass

    Returns:
        Result from tool
    """
    print(f"Executing {tool_name} with {arguments}")
    return {"status": "success", "tool": tool_name, "args": arguments}


async def main():
    """Example usage of the middleware library."""
    # Initialize detection engine
    detection = DetectionEngine(
        allowlist=["write_file", "delete_file"],  # Explicit mutating tools
        enable_convention=True,  # Enable prefix/suffix detection
        enable_metadata=True,  # Check descriptions for keywords
    )

    # Initialize explain engine
    explain = ExplainEngine()

    # Initialize Slack (optional - can be None for testing)
    slack_token = "xoxb-your-token-here"  # Replace with actual token
    slack_client = SlackClient(token=slack_token, channel="#approvals")
    slack_handler = SlackHandler(client=slack_client.client)

    # Initialize local approval (provides native dialogs and file-based approval)
    # Set use_native_dialog=True for macOS/Windows GUI popups, False for file-based only
    local_approval = LocalApproval(
        use_native_dialog=True,  # Use OS native dialogs
        use_file_based=True,  # Also show file-based instructions
    )

    # Initialize approval manager
    approval_manager = ApprovalManager(
        slack_client=slack_client,
        slack_handler=slack_handler,
        local_approval=local_approval,
        default_timeout_seconds=300,  # 5 minutes
        use_local_fallback=True,  # Use local approval if Slack fails
    )

    # Initialize middleware
    middleware = Middleware(
        detection_engine=detection,
        explain_engine=explain,
        approval_manager=approval_manager,
        upstream_tool_call=example_tool_call,
    )

    # Example 1: Non-mutating tool (passes through)
    print("\n=== Example 1: Non-mutating tool ===")
    try:
        result = await middleware.call_tool(
            tool_name="read_file",
            arguments={"path": "/tmp/test.txt"},
            tool_description="Reads the contents of a file",
        )
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")

    # Example 2: Mutating tool (requires approval)
    print("\n=== Example 2: Mutating tool ===")
    try:
        result = await middleware.call_tool(
            tool_name="write_file",
            arguments={"path": "/tmp/test.txt", "content": "Hello, World!"},
            tool_description="Writes content to a file",
        )
        print(f"Result: {result}")
    except PermissionError as e:
        print(f"Approval required/rejected: {e}")
    except Exception as e:
        print(f"Error: {e}")


async def main_with_settings():
    """Example using Settings for configuration (recommended for production).

    This approach uses environment variables and the Settings class,
    which is how the server/proxy.py implementation works.
    """
    from config.settings import Settings

    # Load settings from environment variables (.env file)
    settings = Settings.from_env()

    # Initialize detection engine from settings
    detection = DetectionEngine(
        allowlist=settings.detection.allowlist if settings.detection.allowlist else None,
        blocklist=settings.detection.blocklist if settings.detection.blocklist else None,
        enable_convention=settings.detection.enable_convention,
        enable_metadata=settings.detection.enable_metadata,
    )

    # Initialize explain engine
    explain = ExplainEngine()

    # Initialize Slack from settings (if configured)
    slack_client = None
    slack_handler = None
    if settings.enable_slack and settings.slack:
        slack_client = SlackClient(
            token=settings.slack.token,
            channel=settings.slack.channel,
            user_id=settings.slack.user_id,
        )
        slack_handler = SlackHandler(client=slack_client.client)

    # Initialize local approval from settings
    local_approval = None
    if settings.use_local_approval:
        local_approval = LocalApproval(
            use_native_dialog=settings.use_gui_approval,
            use_file_based=True,
        )

    # Initialize approval manager
    approval_manager = ApprovalManager(
        slack_client=slack_client,
        slack_handler=slack_handler,
        local_approval=local_approval,
        default_timeout_seconds=settings.approval_timeout_seconds,
        use_local_fallback=True,
    )

    # Initialize middleware
    middleware = Middleware(
        detection_engine=detection,
        explain_engine=explain,
        approval_manager=approval_manager,
    )

    # Use middleware same as in main() example above
    print("\n=== Example with Settings (from .env) ===")
    print("See .env.example for configuration options")


if __name__ == "__main__":
    # Run the hardcoded example
    asyncio.run(main())

    # Uncomment to run the Settings-based example instead:
    # asyncio.run(main_with_settings())

