"""Approval workflow state management."""

import asyncio
import sys
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Dict, Optional

from cite_before_act.slack.client import SlackClient
from cite_before_act.slack.handlers import SlackHandler
from cite_before_act.local_approval import LocalApproval


class ApprovalStatus(Enum):
    """Status of an approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


class ApprovalRequest:
    """Represents a single approval request."""

    def __init__(
        self,
        approval_id: str,
        tool_name: str,
        arguments: dict,
        description: str,
        timeout_seconds: int = 300,
    ):
        """Initialize approval request.

        Args:
            approval_id: Unique ID for this approval
            tool_name: Name of the tool requesting approval
            arguments: Arguments to be passed to the tool
            description: Human-readable description of the action
            timeout_seconds: Seconds before request times out (default 5 minutes)
        """
        self.approval_id = approval_id
        self.tool_name = tool_name
        self.arguments = arguments
        self.description = description
        self.status = ApprovalStatus.PENDING
        self.created_at = datetime.now()
        self.timeout_at = self.created_at + timedelta(seconds=timeout_seconds)
        self.resolved_at: Optional[datetime] = None
        self._resolved_event = asyncio.Event()

    def is_expired(self) -> bool:
        """Check if the approval request has expired.

        Returns:
            True if expired, False otherwise
        """
        return datetime.now() > self.timeout_at

    def resolve(self, approved: bool) -> None:
        """Resolve the approval request.

        Args:
            approved: Whether the action was approved
        """
        self.status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        self.resolved_at = datetime.now()
        self._resolved_event.set()

    def timeout(self) -> None:
        """Mark the approval request as timed out."""
        self.status = ApprovalStatus.TIMEOUT
        self.resolved_at = datetime.now()
        self._resolved_event.set()

    async def wait_for_resolution(self, timeout: Optional[float] = None) -> bool:
        """Wait for the approval request to be resolved.

        Args:
            timeout: Optional timeout in seconds

        Returns:
            True if approved, False if rejected or timed out
        """
        try:
            await asyncio.wait_for(self._resolved_event.wait(), timeout=timeout)
            return self.status == ApprovalStatus.APPROVED
        except asyncio.TimeoutError:
            return False


class ApprovalManager:
    """Manages approval workflow state and integrates with Slack."""

    def __init__(
        self,
        slack_client: Optional[SlackClient] = None,
        slack_handler: Optional[SlackHandler] = None,
        local_approval: Optional[LocalApproval] = None,
        default_timeout_seconds: int = 300,
        use_local_fallback: bool = True,
    ):
        """Initialize approval manager.

        Args:
            slack_client: Optional Slack client for sending approval requests
            slack_handler: Optional Slack handler for receiving responses
            local_approval: Optional local approval handler (CLI/GUI)
            default_timeout_seconds: Default timeout for approval requests
            use_local_fallback: If True, use local approval if Slack fails or isn't configured
        """
        self.slack_client = slack_client
        self.slack_handler = slack_handler
        self.local_approval = local_approval
        self.use_local_fallback = use_local_fallback
        self.default_timeout_seconds = default_timeout_seconds
        self._pending_approvals: Dict[str, ApprovalRequest] = {}
        self._cleanup_task: Optional[asyncio.Task] = None

        # Register handler callback if available
        if self.slack_handler:
            # We'll register callbacks per-request, but set up the handler
            pass

    async def request_approval(
        self,
        tool_name: str,
        arguments: dict,
        description: str,
        timeout_seconds: Optional[int] = None,
    ) -> tuple[str, asyncio.Task]:
        """Request approval for a tool call.

        Args:
            tool_name: Name of the tool requesting approval
            arguments: Arguments to be passed to the tool
            description: Human-readable description of the action
            timeout_seconds: Optional timeout override

        Returns:
            Tuple of (approval_id, wait_task) where wait_task resolves to True if approved
        """
        approval_id = str(uuid.uuid4())
        timeout = timeout_seconds or self.default_timeout_seconds

        # Create approval request
        request = ApprovalRequest(
            approval_id=approval_id,
            tool_name=tool_name,
            arguments=arguments,
            description=description,
            timeout_seconds=timeout,
        )

        self._pending_approvals[approval_id] = request

        # Send Slack message if client available
        slack_sent = False
        if self.slack_client:
            try:
                self.slack_client.send_approval_request(
                    approval_id=approval_id,
                    tool_name=tool_name,
                    description=description,
                    arguments=arguments,
                )
                slack_sent = True

                # Register callback with handler
                if self.slack_handler:
                    self.slack_handler.register_approval_callback(
                        approval_id,
                        lambda aid, approved: self._handle_approval_response(aid, approved),
                    )
            except Exception as e:
                # Log error but continue
                print(f"Error sending Slack approval request: {e}", file=sys.stderr)
                slack_sent = False

        # If Slack not available or failed, and local fallback is enabled, use local approval
        if not slack_sent and self.use_local_fallback:
            if not self.local_approval:
                # Create local approval handler if not provided
                # Default to file-based for headless environments (Claude Desktop stdio)
                use_gui = os.getenv("USE_GUI_APPROVAL", "false").lower() == "true"
                self.local_approval = LocalApproval(use_gui=use_gui)
            
            # Request local approval asynchronously
            print(f"Requesting local approval for {tool_name}...", file=sys.stderr, flush=True)
            asyncio.create_task(self._request_local_approval(approval_id, tool_name, description, arguments))

        # Start cleanup task if not already running
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_expired_approvals())

        # Return approval ID and wait task
        wait_task = asyncio.create_task(request.wait_for_resolution(timeout=timeout))
        return approval_id, wait_task

    def _handle_approval_response(self, approval_id: str, approved: bool) -> None:
        """Handle an approval response from Slack.

        Args:
            approval_id: Unique approval ID
            approved: Whether the action was approved
        """
        request = self._pending_approvals.get(approval_id)
        if request and request.status == ApprovalStatus.PENDING:
            request.resolve(approved)

    async def get_approval_status(self, approval_id: str) -> Optional[ApprovalStatus]:
        """Get the status of an approval request.

        Args:
            approval_id: Unique approval ID

        Returns:
            Approval status or None if not found
        """
        request = self._pending_approvals.get(approval_id)
        if request:
            if request.is_expired() and request.status == ApprovalStatus.PENDING:
                request.timeout()
            return request.status
        return None

    async def wait_for_approval(self, approval_id: str, timeout: Optional[float] = None) -> bool:
        """Wait for an approval request to be resolved.

        Args:
            approval_id: Unique approval ID
            timeout: Optional timeout in seconds

        Returns:
            True if approved, False otherwise
        """
        request = self._pending_approvals.get(approval_id)
        if not request:
            return False

        return await request.wait_for_resolution(timeout=timeout)

    async def _request_local_approval(
        self,
        approval_id: str,
        tool_name: str,
        description: str,
        arguments: dict,
    ) -> None:
        """Request approval via local mechanism.

        Args:
            approval_id: Unique approval ID
            tool_name: Name of the tool
            description: Description of the action
            arguments: Arguments that would be passed
        """
        if not self.local_approval:
            return

        try:
            approved = await self.local_approval.request_approval(
                tool_name=tool_name,
                description=description,
                arguments=arguments,
            )
            self._handle_approval_response(approval_id, approved)
        except Exception as e:
            print(f"Error in local approval: {e}", file=sys.stderr)
            # Default to rejection on error
            self._handle_approval_response(approval_id, False)

    def cancel_approval(self, approval_id: str) -> None:
        """Cancel a pending approval request.

        Args:
            approval_id: Unique approval ID
        """
        request = self._pending_approvals.get(approval_id)
        if request and request.status == ApprovalStatus.PENDING:
            request.resolve(False)
        self._pending_approvals.pop(approval_id, None)

        # Unregister callback
        if self.slack_handler:
            self.slack_handler.unregister_approval_callback(approval_id)

    async def _cleanup_expired_approvals(self) -> None:
        """Background task to clean up expired approvals."""
        while True:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds

                now = datetime.now()
                expired_ids = []

                for approval_id, request in self._pending_approvals.items():
                    if request.is_expired() and request.status == ApprovalStatus.PENDING:
                        request.timeout()
                        expired_ids.append(approval_id)

                # Remove expired requests after a delay
                for approval_id in expired_ids:
                    # Keep for a bit in case we need to check status
                    await asyncio.sleep(60)
                    self._pending_approvals.pop(approval_id, None)
                    if self.slack_handler:
                        self.slack_handler.unregister_approval_callback(approval_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in cleanup task: {e}")

