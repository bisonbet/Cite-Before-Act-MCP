"""Handlers for Microsoft Teams bot invoke activities."""

import sys
from typing import Callable, Dict, Any
from botbuilder.core import ActivityHandler, TurnContext
from botbuilder.schema import (
    Activity,
    ActivityTypes,
    InvokeResponse,
    Attachment,
)


class TeamsHandler(ActivityHandler):
    """
    Activity handler for Teams bot to process approval button clicks.

    This class extends the Bot Framework ActivityHandler to handle
    Action.Execute invoke activities from adaptive cards.
    """

    def __init__(self, on_conversation_reference: Callable = None):
        """
        Initialize Teams handler.

        Args:
            on_conversation_reference: Optional callback to save conversation references
        """
        super().__init__()
        self.callbacks: Dict[str, Callable[[str, bool], None]] = {}
        self.on_conversation_reference = on_conversation_reference

    def register_approval_callback(
        self, approval_id: str, callback: Callable[[str, bool], None]
    ) -> None:
        """
        Register a callback to be invoked when an approval response is received.

        Args:
            approval_id: Unique identifier for the approval request
            callback: Function to call with (approval_id, approved) when response received
        """
        self.callbacks[approval_id] = callback
        print(
            f"📝 Registered Teams callback for approval {approval_id[:8]}...",
            file=sys.stderr,
        )

    async def on_message_activity(self, turn_context: TurnContext):
        """
        Handle incoming message activities.

        Args:
            turn_context: Turn context for the message
        """
        # Store conversation reference for proactive messaging
        if self.on_conversation_reference:
            try:
                self.on_conversation_reference(turn_context)
            except Exception as e:
                print(
                    f"⚠️ Error storing Teams conversation reference: {e}",
                    file=sys.stderr,
                )

        # Echo back for basic interaction (can be customized)
        text = turn_context.activity.text.strip()
        if text:
            response = (
                f"Received: {text}\n\n"
                "This is an approval bot. Use the adaptive cards to approve/reject actions."
            )
            await turn_context.send_activity(response)

    async def on_members_added_activity(
        self, members_added: list, turn_context: TurnContext
    ):
        """
        Handle when the bot is added to a conversation.

        Args:
            members_added: List of members added
            turn_context: Turn context for the activity
        """
        # Store conversation reference
        if self.on_conversation_reference:
            try:
                self.on_conversation_reference(turn_context)
            except Exception as e:
                print(
                    f"⚠️ Error storing Teams conversation reference: {e}",
                    file=sys.stderr,
                )

        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity(
                    "Hello! I'm the approval bot. "
                    "I'll send you approval requests when actions need your permission."
                )

    async def on_invoke_activity(self, turn_context: TurnContext) -> InvokeResponse:
        """
        Handle invoke activities (including adaptive card actions).

        Args:
            turn_context: Turn context for the invoke activity

        Returns:
            InvokeResponse with status and optional body
        """
        # Check if this is an adaptive card action
        if turn_context.activity.name == "adaptiveCard/action":
            return await self.on_adaptive_card_invoke(turn_context)

        # Default invoke response
        return InvokeResponse(status=200)

    async def on_adaptive_card_invoke(self, turn_context: TurnContext) -> InvokeResponse:
        """
        Handle adaptive card Action.Execute invokes.

        Args:
            turn_context: Turn context for the invoke activity

        Returns:
            InvokeResponse with updated card or status
        """
        try:
            # Extract the action data
            action_data = turn_context.activity.value
            verb = action_data.get("action", {}).get("verb")
            data = action_data.get("action", {}).get("data", {})

            approval_id = data.get("approval_id")
            action_type = data.get("action")

            if not approval_id or not action_type:
                print(
                    f"⚠️ Teams adaptive card action missing required fields: {data}",
                    file=sys.stderr,
                )
                return InvokeResponse(
                    status=400,
                    body={"error": "Missing approval_id or action in data"},
                )

            # Determine if approved
            approved = action_type == "approve"

            print(
                f"{'✅' if approved else '❌'} Teams approval response received: "
                f"{approval_id[:8]}... -> {action_type}",
                file=sys.stderr,
            )

            # Write approval response to file for MCP server to read
            # (webhook server and MCP server are separate processes)
            import json
            import time
            approval_file = f"/tmp/cite-before-act-teams-approval-{approval_id}.json"
            try:
                with open(approval_file, "w") as f:
                    json.dump({
                        "approval_id": approval_id,
                        "approved": approved,
                        "platform": "teams",
                        "timestamp": time.time(),
                    }, f)
                print(
                    f"Wrote teams approval: {approval_id} -> {approved}",
                    file=sys.stderr,
                    flush=True,
                )
            except Exception as write_error:
                print(
                    f"Error writing teams approval file: {write_error}",
                    file=sys.stderr,
                    flush=True,
                )

            # Update approval cards on all platforms
            try:
                from cite_before_act.approval_messages import get_message_references
                self._update_all_platforms(approval_id, approved, "teams")
            except Exception as update_error:
                print(
                    f"⚠️ Warning: Could not update other platform cards: {update_error}",
                    file=sys.stderr,
                )

            # Trigger the registered callback (for in-process handlers)
            self._trigger_callback(approval_id, approved)

            # Build response card
            from .client import TeamsClient

            status_text = "✅ Approved" if approved else "❌ Rejected"
            response_card = TeamsClient.build_response_card(
                status_text,
                f"The action has been {action_type}d."
            )

            # Return invoke response with updated card
            # For Action.Execute, return the card directly in the body
            return InvokeResponse(
                status=200,
                body=response_card,
            )

        except Exception as e:
            error_msg = f"Error handling Teams adaptive card action: {e}"
            print(f"❌ {error_msg}", file=sys.stderr)
            return InvokeResponse(
                status=500,
                body={"error": error_msg},
            )

    def _trigger_callback(self, approval_id: str, approved: bool) -> None:
        """
        Trigger the registered callback for an approval.

        Args:
            approval_id: Approval request ID
            approved: Whether the request was approved
        """
        callback = self.callbacks.get(approval_id)
        if callback:
            try:
                callback(approval_id, approved)
                print(
                    f"✅ Teams callback triggered for {approval_id[:8]}...",
                    file=sys.stderr,
                )
            except Exception as e:
                print(
                    f"❌ Error in Teams approval callback: {e}",
                    file=sys.stderr,
                )
        else:
            print(
                f"⚠️ No Teams callback registered for {approval_id[:8]}...",
                file=sys.stderr,
            )

    def unregister_callback(self, approval_id: str) -> None:
        """
        Remove a registered callback.

        Args:
            approval_id: Approval request ID
        """
        if approval_id in self.callbacks:
            del self.callbacks[approval_id]
            print(
                f"🗑️ Unregistered Teams callback for {approval_id[:8]}...",
                file=sys.stderr,
            )

    def _update_all_platforms(self, approval_id: str, approved: bool, responding_platform: str) -> None:
        """
        Update approval cards on all platforms when approval received.

        Args:
            approval_id: Approval request ID
            approved: Whether the request was approved
            responding_platform: Platform that responded (e.g., "teams")
        """
        try:
            from cite_before_act.approval_messages import get_message_references
            message_refs = get_message_references(approval_id)

            if not message_refs:
                return

            status_text = "✅ Approved" if approved else "❌ Rejected"
            action_text = "approved" if approved else "rejected"

            # Update Slack card
            if "slack" in message_refs:
                try:
                    from slack_sdk import WebClient
                    import os
                    slack_token = os.getenv("SLACK_BOT_TOKEN")
                    if slack_token:
                        slack_client = WebClient(token=slack_token)
                        ref = message_refs["slack"]
                        slack_client.chat_update(
                            channel=ref["channel"],
                            ts=ref["ts"],
                            text=f"{status_text}: {approval_id[:8]}...",
                            blocks=[
                                {
                                    "type": "section",
                                    "text": {
                                        "type": "mrkdwn",
                                        "text": f"*{status_text}*\n\nApproval `{approval_id[:8]}...` was {action_text} via {responding_platform.title()}."
                                    }
                                }
                            ]
                        )
                        print(f"✅ Updated Slack card for approval {approval_id[:8]}...", file=sys.stderr)
                except Exception as e:
                    print(f"⚠️ Could not update Slack card: {e}", file=sys.stderr)

            # Send Webex follow-up message
            if "webex" in message_refs:
                try:
                    from webexteamssdk import WebexTeamsAPI
                    import os
                    webex_token = os.getenv("WEBEX_BOT_TOKEN")
                    if webex_token:
                        webex_api = WebexTeamsAPI(access_token=webex_token)
                        ref = message_refs["webex"]
                        webex_api.messages.create(
                            roomId=ref["room_id"],
                            text=f"{status_text}: Approval `{approval_id[:8]}...` was {action_text} via {responding_platform.title()}."
                        )
                        print(f"✅ Sent Webex follow-up for approval {approval_id[:8]}...", file=sys.stderr)
                except Exception as e:
                    print(f"⚠️ Could not send Webex follow-up: {e}", file=sys.stderr)

            # Send Teams follow-up message
            if "teams" in message_refs:
                try:
                    # Import Teams client for sending follow-up
                    import asyncio
                    from .client import TeamsClient
                    from .adapter import create_teams_adapter

                    teams_token_id = os.getenv("TEAMS_APP_ID")
                    teams_password = os.getenv("TEAMS_APP_PASSWORD")
                    teams_tenant = os.getenv("TEAMS_TENANT_ID")

                    if teams_token_id and teams_password:
                        adapter = create_teams_adapter(teams_token_id, teams_password, teams_tenant)
                        teams_client = TeamsClient(
                            adapter=adapter,
                            service_url=os.getenv("TEAMS_SERVICE_URL", "https://smba.trafficmanager.net/amer/"),
                            tenant_id=teams_tenant,
                        )

                        # Send follow-up notification
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            loop.run_until_complete(
                                teams_client.send_notification(
                                    f"{status_text}: Approval `{approval_id[:8]}...` was {action_text} via {responding_platform.title()}."
                                )
                            )
                            print(f"✅ Sent Teams follow-up for approval {approval_id[:8]}...", file=sys.stderr)
                        finally:
                            loop.close()
                except Exception as e:
                    print(f"⚠️ Could not send Teams follow-up: {e}", file=sys.stderr)

        except Exception as e:
            print(f"❌ Error in _update_all_platforms: {e}", file=sys.stderr)
