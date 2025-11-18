"""Webex client for sending approval requests with interactive cards."""

import sys
import json
from typing import Optional, Dict, Any
from webexteamssdk import WebexTeamsAPI
from webexteamssdk.exceptions import ApiError


class WebexClient:
    """Client for interacting with Webex Teams API to send approval requests."""

    def __init__(self, access_token: str, room_id: Optional[str] = None,
                 person_email: Optional[str] = None):
        """
        Initialize Webex client.

        Args:
            access_token: Webex bot access token
            room_id: Default room/space ID to send messages to
            person_email: Alternative - send direct message to this email
        """
        self.api = WebexTeamsAPI(access_token=access_token)
        self.room_id = room_id
        self.person_email = person_email

        if not room_id and not person_email:
            raise ValueError("Either room_id or person_email must be provided")

    def send_approval_request(
        self,
        approval_id: str,
        tool_name: str,
        description: str,
        arguments: dict,
    ) -> bool:
        """
        Send an approval request to Webex with interactive card.

        Args:
            approval_id: Unique identifier for this approval request
            tool_name: Name of the tool requiring approval
            description: Human-readable description of the action
            arguments: Tool arguments (will be summarized if large)

        Returns:
            True if message sent successfully, False otherwise
        """
        try:
            # Build the adaptive card
            card_content = self._build_approval_card(
                approval_id, tool_name, description, arguments
            )

            attachment = {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": card_content
            }

            # Send message
            if self.room_id:
                self.api.messages.create(
                    roomId=self.room_id,
                    text=f"Approval Required: {tool_name}",
                    attachments=[attachment]
                )
            else:
                self.api.messages.create(
                    toPersonEmail=self.person_email,
                    text=f"Approval Required: {tool_name}",
                    attachments=[attachment]
                )

            print(
                f"✅ Webex approval request sent for {tool_name} "
                f"(ID: {approval_id[:8]}...)",
                file=sys.stderr
            )
            return True

        except ApiError as e:
            print(
                f"❌ Failed to send Webex approval request: {e}",
                file=sys.stderr
            )
            return False
        except Exception as e:
            print(
                f"❌ Unexpected error sending Webex approval: {e}",
                file=sys.stderr
            )
            return False

    def _build_approval_card(
        self,
        approval_id: str,
        tool_name: str,
        description: str,
        arguments: dict,
    ) -> dict:
        """
        Build adaptive card JSON for approval request.

        Args:
            approval_id: Unique identifier for this approval request
            tool_name: Name of the tool requiring approval
            description: Human-readable description of the action
            arguments: Tool arguments

        Returns:
            Adaptive card JSON structure
        """
        # Summarize arguments for display
        args_summary = self._summarize_arguments(arguments)

        card = {
            "type": "AdaptiveCard",
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.3",
            "body": [
                {
                    "type": "Container",
                    "style": "warning",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "🔒 Approval Required",
                            "size": "Large",
                            "weight": "Bolder",
                            "color": "Attention"
                        }
                    ]
                },
                {
                    "type": "FactSet",
                    "facts": [
                        {
                            "title": "Tool:",
                            "value": f"`{tool_name}`"
                        },
                        {
                            "title": "Approval ID:",
                            "value": f"`{approval_id[:8]}...`"
                        }
                    ]
                },
                {
                    "type": "TextBlock",
                    "text": "**Action:**",
                    "weight": "Bolder",
                    "spacing": "Medium"
                },
                {
                    "type": "TextBlock",
                    "text": description,
                    "wrap": True,
                    "spacing": "Small"
                }
            ],
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "✅ Approve",
                    "style": "positive",
                    "data": {
                        "action": "approve",
                        "approval_id": approval_id,
                        "tool_name": tool_name
                    }
                },
                {
                    "type": "Action.Submit",
                    "title": "❌ Reject",
                    "style": "destructive",
                    "data": {
                        "action": "reject",
                        "approval_id": approval_id,
                        "tool_name": tool_name
                    }
                }
            ]
        }

        # Add arguments section if there are any
        if args_summary:
            card["body"].append({
                "type": "TextBlock",
                "text": "**Arguments:**",
                "weight": "Bolder",
                "spacing": "Medium"
            })
            card["body"].append({
                "type": "TextBlock",
                "text": args_summary,
                "wrap": True,
                "spacing": "Small",
                "isSubtle": True
            })

        return card

    def _summarize_arguments(self, arguments: dict) -> str:
        """
        Summarize arguments for display in card.

        Args:
            arguments: Tool arguments

        Returns:
            Formatted string summary of arguments
        """
        if not arguments:
            return ""

        summary_parts = []
        for key, value in arguments.items():
            # Summarize large values
            if isinstance(value, str) and len(value) > 100:
                summary_parts.append(f"• **{key}**: _{len(value)} characters_")
            elif isinstance(value, (list, dict)):
                if isinstance(value, list) and len(value) > 5:
                    summary_parts.append(f"• **{key}**: _{len(value)} items_")
                elif isinstance(value, dict) and len(str(value)) > 100:
                    summary_parts.append(f"• **{key}**: _{{...}} ({len(value)} keys)_")
                else:
                    summary_parts.append(f"• **{key}**: `{json.dumps(value)[:100]}`")
            else:
                summary_parts.append(f"• **{key}**: `{value}`")

        return "\n".join(summary_parts)

    def send_notification(self, message: str) -> bool:
        """
        Send a simple notification message to Webex.

        Args:
            message: Message text to send

        Returns:
            True if message sent successfully, False otherwise
        """
        try:
            if self.room_id:
                self.api.messages.create(roomId=self.room_id, markdown=message)
            else:
                self.api.messages.create(toPersonEmail=self.person_email, markdown=message)
            return True
        except ApiError as e:
            print(f"❌ Failed to send Webex notification: {e}", file=sys.stderr)
            return False

    def update_message(self, message_id: str, new_text: str) -> bool:
        """
        Update an existing Webex message.

        Note: Webex doesn't support editing messages with cards,
        so this is mainly for text-only notifications.

        Args:
            message_id: ID of message to update
            new_text: New message text

        Returns:
            True if successful, False otherwise
        """
        try:
            # Note: Webex API doesn't support updating messages
            # This is a limitation of the platform
            print(
                "⚠️ Webex doesn't support message updates. "
                "Sending new notification instead.",
                file=sys.stderr
            )
            return self.send_notification(new_text)
        except Exception as e:
            print(f"❌ Failed to update Webex message: {e}", file=sys.stderr)
            return False
