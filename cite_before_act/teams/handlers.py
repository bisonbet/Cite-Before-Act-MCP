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

            # Trigger the registered callback
            self._trigger_callback(approval_id, approved)

            # Build response card
            from .client import TeamsClient

            status_text = "✅ Approved" if approved else "❌ Rejected"
            response_card = TeamsClient.build_response_card(
                status_text,
                f"The action has been {action_type}d."
            )

            # Return invoke response with updated card
            return InvokeResponse(
                status=200,
                body={
                    "statusCode": 200,
                    "type": "application/vnd.microsoft.card.adaptive",
                    "value": response_card,
                },
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
