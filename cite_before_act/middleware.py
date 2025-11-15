"""Middleware for intercepting and requiring approval for mutating tool calls."""

from typing import Any, Callable, Dict, Optional

from cite_before_act.approval import ApprovalManager
from cite_before_act.debug import debug_log
from cite_before_act.detection import DetectionEngine
from cite_before_act.explain import ExplainEngine


class Middleware:
    """Middleware that intercepts tool calls and requires approval for mutating operations."""

    def __init__(
        self,
        detection_engine: DetectionEngine,
        explain_engine: ExplainEngine,
        approval_manager: ApprovalManager,
        upstream_tool_call: Optional[Callable] = None,
    ):
        """Initialize middleware.

        Args:
            detection_engine: Engine for detecting mutating tools
            explain_engine: Engine for generating previews
            approval_manager: Manager for approval workflows
            upstream_tool_call: Optional function to call upstream tools
        """
        self.detection_engine = detection_engine
        self.explain_engine = explain_engine
        self.approval_manager = approval_manager
        self.upstream_tool_call = upstream_tool_call

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        tool_description: Optional[str] = None,
        tool_schema: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Intercept and process a tool call.

        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool
            tool_description: Optional description of the tool
            tool_schema: Optional JSON schema of the tool

        Returns:
            Result from the tool call

        Raises:
            PermissionError: If approval was rejected or timed out
            RuntimeError: If upstream tool call is not configured
        """
        # Check if tool is mutating
        debug_log("Middleware intercepting tool call: '{}'", tool_name)
        is_mutating = self.detection_engine.is_mutating(
            tool_name=tool_name,
            tool_description=tool_description,
            tool_schema=tool_schema,
        )
        debug_log("Tool '{}' is_mutating={}", tool_name, is_mutating)

        if not is_mutating:
            # Non-mutating: pass through directly
            if self.upstream_tool_call:
                return await self._call_upstream(tool_name, arguments)
            else:
                raise RuntimeError("Upstream tool call not configured")

        # Mutating: require approval
        # Generate preview
        description = self.explain_engine.explain(
            tool_name=tool_name,
            arguments=arguments,
            tool_description=tool_description,
        )

        # Request approval
        approval_id, wait_task = await self.approval_manager.request_approval(
            tool_name=tool_name,
            arguments=arguments,
            description=description,
        )

        # Wait for approval
        approved = await wait_task

        if not approved:
            # Check status to provide better error message
            status = await self.approval_manager.get_approval_status(approval_id)
            if status and status.value == "timeout":
                raise PermissionError(
                    f"Approval request for '{tool_name}' timed out. Action not executed."
                )
            else:
                raise PermissionError(
                    f"Approval request for '{tool_name}' was rejected. Action not executed."
                )

        # Approved: execute the tool
        if self.upstream_tool_call:
            return await self._call_upstream(tool_name, arguments)
        else:
            raise RuntimeError("Upstream tool call not configured")

    async def _call_upstream(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Any:
        """Call the upstream tool.

        Args:
            tool_name: Name of the tool
            arguments: Arguments to pass

        Returns:
            Result from upstream tool
        """
        if not self.upstream_tool_call:
            raise RuntimeError("Upstream tool call not configured")

        # Handle both sync and async upstream functions
        result = self.upstream_tool_call(tool_name, arguments)
        if hasattr(result, "__await__"):
            return await result
        return result

    def set_upstream_tool_call(self, upstream_tool_call: Callable) -> None:
        """Set the upstream tool call function.

        Args:
            upstream_tool_call: Function to call upstream tools
        """
        self.upstream_tool_call = upstream_tool_call

