"""Slack API client for sending approval requests."""

import json
from typing import Optional
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


class SlackClient:
    """Client for interacting with Slack API."""

    def __init__(
        self,
        token: str,
        channel: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        """Initialize Slack client.

        Args:
            token: Slack bot token (starts with xoxb-)
            channel: Optional channel ID or name to send messages to
            user_id: Optional user ID to send direct messages to
        """
        self.client = WebClient(token=token)
        self.channel = channel
        self.user_id = user_id

    def send_approval_request(
        self,
        approval_id: str,
        tool_name: str,
        description: str,
        arguments: dict,
    ) -> str:
        """Send an approval request message to Slack.

        Args:
            approval_id: Unique ID for this approval request
            tool_name: Name of the tool requesting approval
            description: Human-readable description of the action
            arguments: Arguments that would be passed to the tool

        Returns:
            Timestamp of the sent message

        Raises:
            SlackApiError: If message sending fails
        """
        # Format arguments for display
        args_text = json.dumps(arguments, indent=2)

        # Build message blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🔒 Approval Required",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Tool:*\n`{tool_name}`",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Approval ID:*\n`{approval_id}`",
                    },
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Description:*\n{description}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Arguments:*\n```\n{args_text}\n```",
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "✅ Approve",
                            "emoji": True,
                        },
                        "style": "primary",
                        "value": json.dumps({"action": "approve", "approval_id": approval_id}),
                        "action_id": "approve_action",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "❌ Reject",
                            "emoji": True,
                        },
                        "style": "danger",
                        "value": json.dumps({"action": "reject", "approval_id": approval_id}),
                        "action_id": "reject_action",
                    },
                ],
            },
        ]

        # Determine where to send
        channel = self.channel or self.user_id
        if not channel:
            raise ValueError("Either channel or user_id must be provided")

        try:
            response = self.client.chat_postMessage(
                channel=channel,
                text=f"Approval required for {tool_name}",
                blocks=blocks,
            )
            return response["ts"]
        except SlackApiError as e:
            raise SlackApiError(f"Failed to send approval request: {e.response['error']}") from e

    def update_message(
        self,
        channel: str,
        timestamp: str,
        text: str,
        blocks: Optional[list] = None,
    ) -> None:
        """Update an existing Slack message.

        Args:
            channel: Channel ID where message was sent
            timestamp: Timestamp of the message to update
            text: New text for the message
            blocks: Optional new blocks for the message
        """
        try:
            self.client.chat_update(
                channel=channel,
                ts=timestamp,
                text=text,
                blocks=blocks,
            )
        except SlackApiError as e:
            raise SlackApiError(f"Failed to update message: {e.response['error']}") from e

    def send_notification(self, message: str) -> str:
        """Send a simple notification message.

        Args:
            message: Message text to send

        Returns:
            Timestamp of the sent message
        """
        channel = self.channel or self.user_id
        if not channel:
            raise ValueError("Either channel or user_id must be provided")

        try:
            response = self.client.chat_postMessage(
                channel=channel,
                text=message,
            )
            return response["ts"]
        except SlackApiError as e:
            raise SlackApiError(f"Failed to send notification: {e.response['error']}") from e

