"""FastMCP proxy server with middleware integration."""

import asyncio
from typing import Any, Dict, Optional

from fastmcp import FastMCP

from cite_before_act.approval import ApprovalManager
from cite_before_act.detection import DetectionEngine
from cite_before_act.explain import ExplainEngine
from cite_before_act.middleware import Middleware
from cite_before_act.slack.client import SlackClient
from cite_before_act.slack.handlers import SlackHandler
from config.settings import Settings


class ProxyServer:
    """FastMCP proxy server that wraps upstream servers with approval middleware."""

    def __init__(self, settings: Settings):
        """Initialize proxy server.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.mcp: Optional[FastMCP] = None
        self.middleware: Optional[Middleware] = None
        self.upstream_client = None

        # Initialize components
        self._initialize_components()

    def _initialize_components(self) -> None:
        """Initialize detection, explain, approval, and middleware components."""
        # Detection engine
        detection_config = self.settings.detection
        detection_engine = DetectionEngine(
            allowlist=detection_config.allowlist if detection_config.allowlist else None,
            blocklist=detection_config.blocklist if detection_config.blocklist else None,
            enable_convention=detection_config.enable_convention,
            enable_metadata=detection_config.enable_metadata,
        )

        # Explain engine
        explain_engine = ExplainEngine()

        # Slack integration
        slack_client = None
        slack_handler = None
        if self.settings.enable_slack and self.settings.slack:
            slack_client = SlackClient(
                token=self.settings.slack.token,
                channel=self.settings.slack.channel,
                user_id=self.settings.slack.user_id,
            )
            slack_handler = SlackHandler(client=slack_client.client)

        # Approval manager
        approval_manager = ApprovalManager(
            slack_client=slack_client,
            slack_handler=slack_handler,
            default_timeout_seconds=self.settings.approval_timeout_seconds,
        )

        # Middleware
        self.middleware = Middleware(
            detection_engine=detection_engine,
            explain_engine=explain_engine,
            approval_manager=approval_manager,
        )

    async def _setup_upstream_connection(self) -> None:
        """Set up connection to upstream MCP server."""
        if not self.settings.upstream:
            raise ValueError("Upstream server configuration not provided")

        upstream_config = self.settings.upstream

        # Create FastMCP proxy
        if upstream_config.transport == "stdio" and upstream_config.command:
            # For stdio, we'll need to use FastMCP's proxy capabilities
            # This is a simplified version - actual implementation may vary
            self.mcp = FastMCP("Cite-Before-Act MCP Proxy")
        elif upstream_config.transport in ("http", "sse") and upstream_config.url:
            # For HTTP/SSE, connect to remote server
            self.mcp = FastMCP("Cite-Before-Act MCP Proxy")
            # Note: FastMCP proxy setup would go here
        else:
            raise ValueError("Invalid upstream server configuration")

        # Add explain tool
        @self.mcp.tool()
        async def explain(tool_name: str, arguments: Dict[str, Any]) -> str:
            """Generate a human-readable preview of what a tool would do.

            Args:
                tool_name: Name of the tool
                arguments: Arguments that would be passed to the tool

            Returns:
                Human-readable description
            """
            if self.middleware:
                return self.middleware.explain_engine.explain(
                    tool_name=tool_name,
                    arguments=arguments,
                )
            return f"Would execute {tool_name} with arguments {arguments}"

        # Set up middleware to call upstream tools
        if self.middleware:
            self.middleware.set_upstream_tool_call(self._call_upstream_tool)

    async def _call_upstream_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on the upstream server.

        Args:
            tool_name: Name of the tool
            arguments: Arguments to pass

        Returns:
            Result from upstream tool
        """
        if not self.mcp:
            raise RuntimeError("MCP server not initialized")

        # Use FastMCP's tool calling mechanism
        # This is a simplified version - actual implementation depends on FastMCP API
        # In practice, we'd use the upstream client to call tools
        raise NotImplementedError("Upstream tool calling needs FastMCP client implementation")

    async def create_server(self) -> FastMCP:
        """Create and configure the FastMCP server.

        Returns:
            Configured FastMCP server instance
        """
        await self._setup_upstream_connection()

        if not self.mcp:
            raise RuntimeError("Failed to create MCP server")

        # Override tool call handler to use middleware
        # This is a simplified version - actual implementation depends on FastMCP API
        # We need to intercept tool calls and route through middleware

        return self.mcp

    def run(
        self,
        transport: str = "stdio",
        host: str = "127.0.0.1",
        port: int = 8000,
    ) -> None:
        """Run the proxy server.

        Args:
            transport: Transport type (stdio, http, sse)
            host: Host for HTTP/SSE transport
            port: Port for HTTP/SSE transport
        """
        if not self.mcp:
            # Create server synchronously for stdio
            asyncio.run(self.create_server())

        if self.mcp:
            if transport == "stdio":
                self.mcp.run(transport="stdio")
            elif transport == "http":
                self.mcp.run(transport="http", host=host, port=port)
            elif transport == "sse":
                self.mcp.run(transport="sse", host=host, port=port)
            else:
                raise ValueError(f"Unsupported transport: {transport}")

