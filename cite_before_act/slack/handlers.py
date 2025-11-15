"""Handlers for processing Slack interaction events."""

import json
from typing import Callable, Optional
from slack_sdk import WebClient


class SlackHandler:
    """Handler for processing Slack interaction events."""

    def __init__(self, client: Optional[WebClient] = None):
        """Initialize Slack handler.

        Args:
            client: Optional Slack WebClient for responding to interactions
        """
        self.client = client
        self._approval_callbacks: dict[str, Callable[[str, bool], None]] = {}

    def register_approval_callback(
        self,
        approval_id: str,
        callback: Callable[[str, bool], None],
    ) -> None:
        """Register a callback for an approval request.

        Args:
            approval_id: Unique approval ID
            callback: Function to call with (approval_id, approved) when response received
        """
        self._approval_callbacks[approval_id] = callback

    def unregister_approval_callback(self, approval_id: str) -> None:
        """Unregister a callback for an approval request.

        Args:
            approval_id: Unique approval ID
        """
        self._approval_callbacks.pop(approval_id, None)

    def handle_interaction(self, payload: dict) -> dict:
        """Handle a Slack interaction payload.

        Args:
            payload: Slack interaction payload (can be dict or JSON string)

        Returns:
            Response dictionary for Slack
        """
        # Parse payload if it's a string
        if isinstance(payload, str):
            payload = json.loads(payload)

        # Handle button clicks
        if payload.get("type") == "block_actions":
            return self._handle_block_actions(payload)

        # Handle other interaction types if needed
        return {"text": "Interaction received"}

    def _handle_block_actions(self, payload: dict) -> dict:
        """Handle block action interactions (button clicks).

        Args:
            payload: Slack interaction payload

        Returns:
            Response dictionary for Slack
        """
        actions = payload.get("actions", [])
        if not actions:
            return {"text": "No actions found"}

        for action in actions:
            action_id = action.get("action_id")
            value = action.get("value")

            if action_id in ("approve_action", "reject_action") and value:
                try:
                    value_data = json.loads(value) if isinstance(value, str) else value
                    approval_id = value_data.get("approval_id")
                    action_type = value_data.get("action")

                    if approval_id and action_type:
                        approved = action_type == "approve"
                        self._trigger_callback(approval_id, approved)

                        # Update the message to show it was processed
                        if self.client:
                            self._update_interaction_message(payload, approved)

                        return {
                            "text": f"Request {'approved' if approved else 'rejected'}",
                            "response_type": "ephemeral",
                        }
                except (json.JSONDecodeError, KeyError) as e:
                    return {"text": f"Error processing action: {e}"}

        return {"text": "Action processed"}

    def _trigger_callback(self, approval_id: str, approved: bool) -> None:
        """Trigger the registered callback for an approval.

        Args:
            approval_id: Unique approval ID
            approved: Whether the action was approved
        """
        callback = self._approval_callbacks.get(approval_id)
        if callback:
            try:
                callback(approval_id, approved)
            except Exception as e:
                # Log error but don't fail
                print(f"Error in approval callback: {e}")

    def _update_interaction_message(self, payload: dict, approved: bool) -> None:
        """Update the original message to show it was processed.

        Args:
            payload: Slack interaction payload
            approved: Whether the action was approved
        """
        if not self.client:
            return

        try:
            channel = payload.get("channel", {}).get("id")
            message_ts = payload.get("message", {}).get("ts")

            if channel and message_ts:
                status_text = "✅ Approved" if approved else "❌ Rejected"
                self.client.chat_update(
                    channel=channel,
                    ts=message_ts,
                    text=f"Approval request {status_text}",
                    blocks=[
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*{status_text}*\nThis approval request has been processed.",
                            },
                        },
                    ],
                )
        except Exception as e:
            # Log but don't fail
            print(f"Error updating interaction message: {e}")

