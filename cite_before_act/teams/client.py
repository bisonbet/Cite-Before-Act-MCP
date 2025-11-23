"""Microsoft Teams client for sending approval requests via Bot Framework."""

import sys
import json
from typing import Optional, Dict, Any
from botbuilder.schema import (
    Activity,
    ActivityTypes,
    Attachment,
    ConversationReference,
    ConversationAccount,
    ChannelAccount,
)
from botbuilder.core import BotFrameworkAdapter, TurnContext


class TeamsClient:
    """Client for sending approval requests to Microsoft Teams via Bot Framework."""

    def __init__(
        self,
        adapter: BotFrameworkAdapter,
        service_url: str,
        conversation_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ):
        """
        Initialize Teams client.

        Args:
            adapter: Bot Framework adapter
            service_url: Teams service URL (e.g., https://smba.trafficmanager.net/amer/)
            conversation_id: Conversation/channel ID to send messages to
            channel_id: Channel type (usually 'msteams')
            tenant_id: Optional Teams tenant ID
        """
        self.adapter = adapter
        self.service_url = service_url
        self.conversation_id = conversation_id
        self.channel_id = channel_id or "msteams"
        self.tenant_id = tenant_id

        # Store conversation reference for proactive messaging
        self.conversation_reference: Optional[ConversationReference] = None

        if conversation_id:
            # Create a conversation reference for proactive messaging
            self.conversation_reference = ConversationReference(
                service_url=service_url,
                channel_id=self.channel_id,
                conversation=ConversationAccount(
                    id=conversation_id,
                    tenant_id=tenant_id,
                ),
            )

    def set_conversation_reference(self, turn_context: TurnContext) -> None:
        """
        Store conversation reference from a turn context.

        This should be called when the bot receives a message, so we can
        send proactive messages later.

        Args:
            turn_context: Turn context from an incoming message
        """
        self.conversation_reference = TurnContext.get_conversation_reference(
            turn_context.activity
        )
        print(
            f"📝 Stored Teams conversation reference: {self.conversation_reference.conversation.id}",
            file=sys.stderr,
        )

    async def send_approval_request(
        self,
        approval_id: str,
        tool_name: str,
        description: str,
        arguments: dict,
    ) -> bool:
        """
        Send an approval request to Teams with adaptive card.

        Args:
            approval_id: Unique identifier for this approval request
            tool_name: Name of the tool requiring approval
            description: Human-readable description of the action
            arguments: Tool arguments (will be summarized if large)

        Returns:
            True if message sent successfully, False otherwise
        """
        # Try to load conversation reference from file if not already set
        # This is saved by the webhook server when the bot receives messages
        if not self.conversation_reference:
            import os
            import json
            conv_ref_file = "/tmp/cite-before-act-teams-conversation-reference.json"
            if os.path.exists(conv_ref_file):
                try:
                    with open(conv_ref_file, "r") as f:
                        conv_ref_data = json.load(f)
                        conversation_id = conv_ref_data.get("conversation_id")
                        service_url = conv_ref_data.get("service_url")
                        tenant_id = conv_ref_data.get("tenant_id")

                        # Remove message ID suffix if present
                        if conversation_id and ';messageid=' in conversation_id:
                            conversation_id = conversation_id.split(';messageid=')[0]

                        if conversation_id and service_url:
                            self.conversation_reference = ConversationReference(
                                service_url=service_url,
                                channel_id=conv_ref_data.get("channel_id", "msteams"),
                                conversation=ConversationAccount(
                                    id=conversation_id,
                                    tenant_id=tenant_id,
                                ),
                            )
                            print(
                                f"📂 Loaded Teams conversation reference from file: {conversation_id}",
                                file=sys.stderr,
                            )
                except Exception as e:
                    print(
                        f"⚠️ Warning: Could not load Teams conversation reference from file: {e}",
                        file=sys.stderr,
                    )

        if not self.conversation_reference:
            print(
                "❌ No conversation reference set. Cannot send proactive message.\n"
                "   Make sure the Teams bot has been added to a channel and has received at least one message.",
                file=sys.stderr,
            )
            return False

        try:
            # Build the adaptive card
            card_content = self._build_approval_card(
                approval_id, tool_name, description, arguments
            )

            attachment = Attachment(
                content_type="application/vnd.microsoft.card.adaptive",
                content=card_content,
            )

            # Create activity
            activity = Activity(
                type=ActivityTypes.message,
                attachments=[attachment],
                text=f"Approval Required: {tool_name}",
            )

            # Send proactive message
            async def send_activity(turn_context: TurnContext):
                await turn_context.send_activity(activity)

            await self.adapter.continue_conversation(
                self.conversation_reference,
                send_activity,
                self.adapter.settings.app_id,
            )

            print(
                f"✅ Teams approval request sent for {tool_name} "
                f"(ID: {approval_id[:8]}...)",
                file=sys.stderr,
            )
            return True

        except Exception as e:
            print(
                f"❌ Failed to send Teams approval request: {e}",
                file=sys.stderr,
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
            "version": "1.4",
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
                            "color": "Attention",
                        }
                    ],
                },
                {
                    "type": "FactSet",
                    "facts": [
                        {"title": "Tool:", "value": f"`{tool_name}`"},
                        {"title": "Approval ID:", "value": f"`{approval_id[:8]}...`"},
                    ],
                },
                {
                    "type": "TextBlock",
                    "text": "**Action:**",
                    "weight": "Bolder",
                    "spacing": "Medium",
                },
                {
                    "type": "TextBlock",
                    "text": description,
                    "wrap": True,
                    "spacing": "Small",
                },
            ],
            "actions": [
                {
                    "type": "Action.Execute",
                    "title": "✅ Approve",
                    "verb": "approve",
                    "data": {
                        "action": "approve",
                        "approval_id": approval_id,
                        "tool_name": tool_name,
                    },
                    "style": "positive",
                },
                {
                    "type": "Action.Execute",
                    "title": "❌ Reject",
                    "verb": "reject",
                    "data": {
                        "action": "reject",
                        "approval_id": approval_id,
                        "tool_name": tool_name,
                    },
                    "style": "destructive",
                },
            ],
        }

        # Add arguments section if there are any
        if args_summary:
            card["body"].append(
                {
                    "type": "TextBlock",
                    "text": "**Arguments:**",
                    "weight": "Bolder",
                    "spacing": "Medium",
                }
            )
            card["body"].append(
                {
                    "type": "TextBlock",
                    "text": args_summary,
                    "wrap": True,
                    "spacing": "Small",
                    "isSubtle": True,
                }
            )

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

        return "\n\n".join(summary_parts)

    async def send_notification(self, message: str) -> bool:
        """
        Send a simple notification message to Teams.

        Args:
            message: Message text to send

        Returns:
            True if message sent successfully, False otherwise
        """
        if not self.conversation_reference:
            print(
                "❌ No conversation reference set. Cannot send notification.",
                file=sys.stderr,
            )
            return False

        try:
            activity = Activity(type=ActivityTypes.message, text=message)

            async def send_activity(turn_context: TurnContext):
                await turn_context.send_activity(activity)

            await self.adapter.continue_conversation(
                self.conversation_reference,
                send_activity,
                self.adapter.settings.app_id,
            )

            return True

        except Exception as e:
            print(f"❌ Failed to send Teams notification: {e}", file=sys.stderr)
            return False

    @staticmethod
    def build_response_card(status: str, message: str = "") -> dict:
        """
        Build a response card to show after approval/rejection.

        Args:
            status: Status text (e.g., "✅ Approved" or "❌ Rejected")
            message: Optional additional message

        Returns:
            Adaptive card JSON structure
        """
        card = {
            "type": "AdaptiveCard",
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "text": status,
                    "size": "Large",
                    "weight": "Bolder",
                }
            ],
        }

        if message:
            card["body"].append(
                {
                    "type": "TextBlock",
                    "text": message,
                    "wrap": True,
                    "isSubtle": True,
                }
            )

        return card
