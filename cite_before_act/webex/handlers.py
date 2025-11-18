"""Handlers for Webex attachment action webhooks."""

import sys
import json
from typing import Callable, Dict, Optional, Any
from webexteamssdk import WebexTeamsAPI
from webexteamssdk.exceptions import ApiError


class WebexHandler:
    """Handles Webex attachment action webhooks and invokes approval callbacks."""

    def __init__(self, access_token: str):
        """
        Initialize Webex handler.

        Args:
            access_token: Webex bot access token
        """
        self.api = WebexTeamsAPI(access_token=access_token)
        self.callbacks: Dict[str, Callable[[str, bool], None]] = {}

    def register_approval_callback(
        self,
        approval_id: str,
        callback: Callable[[str, bool], None]
    ) -> None:
        """
        Register a callback to be invoked when an approval response is received.

        Args:
            approval_id: Unique identifier for the approval request
            callback: Function to call with (approval_id, approved) when response received
        """
        self.callbacks[approval_id] = callback
        print(
            f"📝 Registered Webex callback for approval {approval_id[:8]}...",
            file=sys.stderr
        )

    def handle_attachment_action(self, webhook_data: dict) -> Dict[str, Any]:
        """
        Handle an attachmentActions webhook from Webex.

        Args:
            webhook_data: Webhook payload from Webex

        Returns:
            Response dict with status and message
        """
        try:
            # Extract attachment action ID from webhook
            attachment_action_id = webhook_data.get("data", {}).get("id")
            if not attachment_action_id:
                return {
                    "status": "error",
                    "message": "Missing attachment action ID"
                }

            # Get full attachment action details from Webex API
            action = self.api.attachment_actions.get(attachment_action_id)

            # Extract the submitted data
            inputs = action.inputs if hasattr(action, 'inputs') else {}
            approval_id = inputs.get("approval_id")
            action_type = inputs.get("action")

            if not approval_id or not action_type:
                print(
                    f"⚠️ Webex attachment action missing required fields: {inputs}",
                    file=sys.stderr
                )
                return {
                    "status": "error",
                    "message": "Missing approval_id or action in submission"
                }

            # Determine if approved
            approved = action_type == "approve"

            print(
                f"{'✅' if approved else '❌'} Webex approval response received: "
                f"{approval_id[:8]}... -> {action_type}",
                file=sys.stderr
            )

            # Trigger the registered callback
            self._trigger_callback(approval_id, approved)

            # Send confirmation message
            person_id = action.personId if hasattr(action, 'personId') else None
            if person_id:
                try:
                    confirmation = (
                        f"✅ **Approved** the action."
                        if approved
                        else f"❌ **Rejected** the action."
                    )
                    self.api.messages.create(
                        toPersonId=person_id,
                        markdown=confirmation
                    )
                except ApiError:
                    pass  # Don't fail if we can't send confirmation

            return {
                "status": "success",
                "approval_id": approval_id,
                "approved": approved
            }

        except ApiError as e:
            error_msg = f"Webex API error: {e}"
            print(f"❌ {error_msg}", file=sys.stderr)
            return {"status": "error", "message": error_msg}

        except Exception as e:
            error_msg = f"Error handling Webex attachment action: {e}"
            print(f"❌ {error_msg}", file=sys.stderr)
            return {"status": "error", "message": error_msg}

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
                    f"✅ Webex callback triggered for {approval_id[:8]}...",
                    file=sys.stderr
                )
            except Exception as e:
                print(
                    f"❌ Error in Webex approval callback: {e}",
                    file=sys.stderr
                )
        else:
            print(
                f"⚠️ No Webex callback registered for {approval_id[:8]}...",
                file=sys.stderr
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
                f"🗑️ Unregistered Webex callback for {approval_id[:8]}...",
                file=sys.stderr
            )

    def create_webhook(self, target_url: str, name: str = "Approval Webhook") -> Optional[str]:
        """
        Create a webhook for attachment actions.

        Args:
            target_url: Public URL to receive webhook events
            name: Name for the webhook

        Returns:
            Webhook ID if successful, None otherwise
        """
        try:
            webhook = self.api.webhooks.create(
                name=name,
                targetUrl=target_url,
                resource="attachmentActions",
                event="created"
            )
            webhook_id = webhook.id if hasattr(webhook, 'id') else None
            print(
                f"✅ Created Webex webhook: {name} -> {target_url}",
                file=sys.stderr
            )
            return webhook_id

        except ApiError as e:
            # Check if webhook already exists
            if "already exists" in str(e).lower():
                print(
                    f"ℹ️ Webex webhook already exists for {target_url}",
                    file=sys.stderr
                )
                # Try to find existing webhook
                try:
                    webhooks = self.api.webhooks.list()
                    for wh in webhooks:
                        if (hasattr(wh, 'targetUrl') and wh.targetUrl == target_url and
                            hasattr(wh, 'resource') and wh.resource == "attachmentActions"):
                            return wh.id
                except Exception:
                    pass
            print(f"❌ Failed to create Webex webhook: {e}", file=sys.stderr)
            return None

        except Exception as e:
            print(f"❌ Unexpected error creating Webex webhook: {e}", file=sys.stderr)
            return None

    def delete_webhook(self, webhook_id: str) -> bool:
        """
        Delete a webhook.

        Args:
            webhook_id: ID of webhook to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            self.api.webhooks.delete(webhook_id)
            print(f"✅ Deleted Webex webhook {webhook_id}", file=sys.stderr)
            return True
        except ApiError as e:
            print(f"❌ Failed to delete Webex webhook: {e}", file=sys.stderr)
            return False

    def list_webhooks(self) -> list:
        """
        List all webhooks for this bot.

        Returns:
            List of webhook objects
        """
        try:
            webhooks = self.api.webhooks.list()
            return list(webhooks)
        except ApiError as e:
            print(f"❌ Failed to list Webex webhooks: {e}", file=sys.stderr)
            return []
