"""Slack API client for sending approval requests."""

import json
import sys
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
            channel: Optional channel ID (C1234567890) or name (#approvals) to send messages to
            user_id: Optional user ID to send direct messages to
        """
        self.client = WebClient(token=token)
        self.channel = channel
        self.user_id = user_id
        self._channel_id = None  # Cached channel ID after resolution

    def _resolve_channel_id(self, channel: str) -> str:
        """Resolve channel name to channel ID if needed.

        Args:
            channel: Channel name (approvals, #approvals) or channel ID (C1234567890 for public, G1234567890 for private)

        Returns:
            Channel ID (C... for public, G... for private)

        Raises:
            SlackApiError: If channel cannot be found
        """
        # If it's already a channel/group ID (starts with C or G), return as-is
        if (channel.startswith("C") or channel.startswith("G")) and len(channel) > 1:
            return channel

        # Remove # prefix if present (private channels don't use #)
        channel_name = channel.lstrip("#")

        try:
            # Try to find the channel by name (searches both public and private)
            # Note: conversations_list only returns channels the bot is a member of
            response = self.client.conversations_list(
                types="public_channel,private_channel",
                exclude_archived=True
            )
            if response["ok"]:
                for ch in response.get("channels", []):
                    if ch["name"] == channel_name:
                        return ch["id"]
            
            # If not found in list, try to get info directly (might work if bot has access)
            try:
                info_response = self.client.conversations_info(channel=channel_name)
                if info_response["ok"]:
                    return info_response["channel"]["id"]
            except SlackApiError:
                pass  # Channel might not exist or bot doesn't have access

            # For public channels, try to join
            if not channel.startswith("#"):  # If no #, might be public
                try:
                    join_response = self.client.conversations_join(channel=channel_name)
                    if join_response["ok"]:
                        info_response = self.client.conversations_info(channel=channel_name)
                        if info_response["ok"]:
                            return info_response["channel"]["id"]
                except SlackApiError:
                    pass  # Channel might be private or doesn't exist

            raise SlackApiError(
                f"Channel '{channel}' not found. Make sure:\n"
                f"  1. The channel exists\n"
                f"  2. The bot is invited to the channel (for private channels: /invite @YourBotName)\n"
                f"  3. You're using the correct channel name (e.g., 'approvals' for private, '#approvals' for public)\n"
                f"  4. Or use the channel ID directly (C1234567890 for public, G1234567890 for private)\n"
                f"  5. The bot has 'groups:read' scope for private channels"
            )
        except SlackApiError:
            raise
        except Exception as e:
            raise SlackApiError(f"Failed to resolve channel '{channel}': {e}")

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

        # Resolve channel name to ID if needed (only for channels, not user IDs)
        # User IDs start with U, channel IDs start with C (public) or G (private)
        if channel.startswith("C") or channel.startswith("G") or channel.startswith("#") or (not channel.startswith("U")):
            # If it's not a user ID and not already resolved, resolve it
            if not self._channel_id and not (channel.startswith("C") or channel.startswith("G")):
                self._channel_id = self._resolve_channel_id(channel)
                channel = self._channel_id
            elif self._channel_id:
                channel = self._channel_id

        try:
            response = self.client.chat_postMessage(
                channel=channel,
                text=f"Approval required for {tool_name}",
                blocks=blocks,
            )
            if not response["ok"]:
                raise SlackApiError(f"Slack API returned error: {response.get('error', 'unknown error')}")
            return response["ts"]
        except SlackApiError as e:
            # Extract error message safely
            error_msg = str(e)
            if hasattr(e, 'response'):
                if isinstance(e.response, dict):
                    error_msg = e.response.get('error', str(e))
                elif hasattr(e.response, 'get'):
                    error_msg = e.response.get('error', str(e))
            
            # Provide helpful error messages
            if 'channel_not_found' in error_msg.lower() or 'not_in_channel' in error_msg.lower():
                print(f"Slack API Error: Channel not found or bot not in channel.", file=sys.stderr, flush=True)
                print(f"  Channel: {self.channel}", file=sys.stderr, flush=True)
                print(f"  Troubleshooting:", file=sys.stderr, flush=True)
                print(f"    1. Make sure the channel exists", file=sys.stderr, flush=True)
                print(f"    2. Invite the bot to the channel: /invite @YourBotName", file=sys.stderr, flush=True)
                print(f"    3. For PRIVATE channels:", file=sys.stderr, flush=True)
                print(f"       - Use channel name WITHOUT # (e.g., 'approvals' not '#approvals')", file=sys.stderr, flush=True)
                print(f"       - Or use group ID starting with G (e.g., G1234567890)", file=sys.stderr, flush=True)
                print(f"       - Bot MUST be invited: /invite @YourBotName", file=sys.stderr, flush=True)
                print(f"    4. For PUBLIC channels:", file=sys.stderr, flush=True)
                print(f"       - Use channel name WITH # (e.g., '#approvals')", file=sys.stderr, flush=True)
                print(f"       - Or use channel ID starting with C (e.g., C1234567890)", file=sys.stderr, flush=True)
            else:
                print(f"Slack API Error: Failed to send approval request: {error_msg}", file=sys.stderr, flush=True)
            # Re-raise to trigger fallback to local approval
            raise
        except Exception as e:
            error_msg = f"Unexpected error sending Slack message: {e}"
            print(f"Slack Error: {error_msg}", file=sys.stderr)
            # Re-raise to trigger fallback to local approval
            raise

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

