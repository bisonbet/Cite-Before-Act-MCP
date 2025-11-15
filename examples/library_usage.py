"""Example: Using Cite-Before-Act as a library."""

import asyncio
from cite_before_act import DetectionEngine, ExplainEngine, ApprovalManager, Middleware
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

    # Initialize approval manager
    approval_manager = ApprovalManager(
        slack_client=slack_client,
        slack_handler=slack_handler,
        default_timeout_seconds=300,  # 5 minutes
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


if __name__ == "__main__":
    asyncio.run(main())

