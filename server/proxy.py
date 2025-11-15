"""FastMCP proxy server with middleware integration."""

import asyncio
import subprocess
from typing import Any, Dict, Optional

from fastmcp import FastMCP
from fastmcp.client import Client
from fastmcp.client.stdio import StdioServerParameters

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
        self.upstream_client: Optional[Client] = None
        self.upstream_tools: Dict[str, Dict[str, Any]] = {}

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

    async def _connect_to_upstream(self) -> None:
        """Connect to the upstream MCP server and fetch its tools."""
        if not self.settings.upstream:
            raise ValueError("Upstream server configuration not provided")

        upstream_config = self.settings.upstream

        if upstream_config.transport == "stdio" and upstream_config.command:
            # Create stdio server parameters
            server_params = StdioServerParameters(
                command=upstream_config.command,
                args=upstream_config.args,
            )

            # Connect to upstream server (don't use context manager - we need to keep it open)
            self.upstream_client = Client(server_params)

            # Initialize the connection
            await self.upstream_client.initialize()

            # List tools from upstream server
            tools_result = await self.upstream_client.list_tools()
            if tools_result and tools_result.tools:
                for tool in tools_result.tools:
                    self.upstream_tools[tool.name] = {
                        "name": tool.name,
                        "description": tool.description or "",
                        "inputSchema": tool.inputSchema or {},
                    }

        elif upstream_config.transport in ("http", "sse") and upstream_config.url:
            # For HTTP/SSE, we'd use a different client setup
            # This is a placeholder for future implementation
            raise NotImplementedError("HTTP/SSE transport not yet implemented")
        else:
            raise ValueError("Invalid upstream server configuration")

    async def _setup_proxy_server(self) -> None:
        """Set up the FastMCP proxy server with upstream tools."""
        # Create FastMCP server
        self.mcp = FastMCP("Cite-Before-Act MCP Proxy")

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

        # Dynamically create proxy tools for each upstream tool
        for tool_name, tool_info in self.upstream_tools.items():
            # Create a closure to capture the tool_name
            def make_tool_handler(name: str, desc: str):
                @self.mcp.tool(name=name, description=desc)
                async def tool_handler(**kwargs: Any) -> Any:
                    """Proxy tool handler that routes through middleware."""
                    if not self.middleware:
                        raise RuntimeError("Middleware not initialized")

                    # Get tool description and schema from upstream
                    tool_desc = self.upstream_tools.get(name, {}).get("description", "")
                    tool_schema = self.upstream_tools.get(name, {}).get("inputSchema", {})

                    # Route through middleware
                    return await self.middleware.call_tool(
                        tool_name=name,
                        arguments=kwargs,
                        tool_description=tool_desc,
                        tool_schema=tool_schema,
                    )
                
                return tool_handler

            # Register the tool with FastMCP
            make_tool_handler(tool_name, tool_info.get("description", f"Proxy for {tool_name}"))

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
        if not self.upstream_client:
            # Reconnect if needed
            await self._connect_to_upstream()

        if not self.upstream_client:
            raise RuntimeError("Upstream client not available")

        # Call the tool on upstream server
        result = await self.upstream_client.call_tool(tool_name, arguments)
        
        # Extract the result content
        if result and result.content:
            # FastMCP returns content as a list, get the first item
            if len(result.content) > 0:
                content_item = result.content[0]
                if hasattr(content_item, "text"):
                    return content_item.text
                elif hasattr(content_item, "data"):
                    return content_item.data
                else:
                    return str(content_item)
        
        return result

    async def create_server(self) -> FastMCP:
        """Create and configure the FastMCP server.

        Returns:
            Configured FastMCP server instance
        """
        # Connect to upstream server first
        await self._connect_to_upstream()

        # Set up proxy server with upstream tools
        await self._setup_proxy_server()

        if not self.mcp:
            raise RuntimeError("Failed to create MCP server")

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
        # Create server first (this connects to upstream and sets up tools)
        asyncio.run(self.create_server())

        if not self.mcp:
            raise RuntimeError("Failed to create MCP server")

        # Run the server (this is blocking and handles the event loop)
        if transport == "stdio":
            self.mcp.run(transport="stdio")
        elif transport == "http":
            self.mcp.run(transport="http", host=host, port=port)
        elif transport == "sse":
            self.mcp.run(transport="sse", host=host, port=port)
        else:
            raise ValueError(f"Unsupported transport: {transport}")
