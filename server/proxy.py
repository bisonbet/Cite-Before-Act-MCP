"""FastMCP proxy server with middleware integration."""

import asyncio
import json
import subprocess
import types
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
        self.upstream_process: Optional[subprocess.Popen] = None
        self.upstream_tools: Dict[str, Dict[str, Any]] = {}
        self._request_id = 3  # Start after init and list_tools

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
            # Start upstream server as subprocess
            self.upstream_process = subprocess.Popen(
                [upstream_config.command] + upstream_config.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0,
            )

            # Initialize MCP connection
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "cite-before-act-proxy", "version": "0.1.0"},
                },
            }

            # Send initialize request
            request_str = json.dumps(init_request) + "\n"
            self.upstream_process.stdin.write(request_str)
            self.upstream_process.stdin.flush()

            # Read initialize response asynchronously
            loop = asyncio.get_event_loop()
            response_line = await loop.run_in_executor(
                None, self.upstream_process.stdout.readline
            )
            if response_line:
                init_response = json.loads(response_line.strip())
                if "error" in init_response:
                    raise RuntimeError(f"Upstream server initialization failed: {init_response['error']}")

            # Send initialized notification
            initialized_notification = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
            }
            self.upstream_process.stdin.write(json.dumps(initialized_notification) + "\n")
            self.upstream_process.stdin.flush()

            # List tools from upstream server
            list_tools_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {},
            }
            self.upstream_process.stdin.write(json.dumps(list_tools_request) + "\n")
            self.upstream_process.stdin.flush()

            # Read tools list response asynchronously
            loop = asyncio.get_event_loop()
            tools_response_line = await loop.run_in_executor(
                None, self.upstream_process.stdout.readline
            )
            if tools_response_line:
                tools_response = json.loads(tools_response_line.strip())
                if "result" in tools_response and "tools" in tools_response["result"]:
                    for tool in tools_response["result"]["tools"]:
                        self.upstream_tools[tool["name"]] = {
                            "name": tool["name"],
                            "description": tool.get("description", ""),
                            "inputSchema": tool.get("inputSchema", {}),
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
            # Get the input schema to understand the parameters
            input_schema = tool_info.get("inputSchema", {})
            properties = input_schema.get("properties", {})
            param_names = list(properties.keys())
            
            # Create a function with explicit parameters using exec
            # FastMCP requires explicit parameters, not **kwargs
            if param_names:
                # Build function signature with all parameters
                params_str = ", ".join(param_names)
                # Build code to collect parameters into dict
                collect_code = "arguments = {" + ", ".join([f"'{p}': {p}" for p in param_names]) + "}"
            else:
                params_str = ""
                collect_code = "arguments = {}"
            
            # Capture variables for closure
            name = tool_name
            desc = tool_info.get("description", "")
            schema = input_schema
            middleware_ref = self.middleware
            tools_ref = self.upstream_tools
            
            # Create function dynamically
            func_def = f"""
async def handler({params_str}):
    \"\"\"{desc}\"\"\"
    {collect_code}
    if not middleware_ref:
        raise RuntimeError("Middleware not initialized")
    tool_desc = tools_ref.get(name, {{}}).get("description", "")
    return await middleware_ref.call_tool(
        tool_name=name,
        arguments=arguments,
        tool_description=tool_desc,
        tool_schema=schema,
    )
"""
            # Execute in local namespace
            local_ns = {
                "middleware_ref": middleware_ref,
                "tools_ref": tools_ref,
                "name": name,
                "schema": schema,
                "asyncio": asyncio,
            }
            exec(func_def, {"asyncio": asyncio}, local_ns)
            handler = local_ns["handler"]
            
            # Register with FastMCP
            self.mcp.tool(name=tool_name, description=desc)(handler)

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
        if not self.upstream_process:
            raise RuntimeError("Upstream process not available")

        # Create tool call request
        request_id = self._request_id
        self._request_id += 1

        tool_request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }

        # Send request to upstream server
        request_str = json.dumps(tool_request) + "\n"
        self.upstream_process.stdin.write(request_str)
        self.upstream_process.stdin.flush()

        # Read response asynchronously
        loop = asyncio.get_event_loop()
        response_line = await loop.run_in_executor(
            None, self.upstream_process.stdout.readline
        )
        if not response_line:
            raise RuntimeError("No response from upstream server")

        response = json.loads(response_line.strip())

        if "error" in response:
            raise RuntimeError(f"Upstream tool call failed: {response['error']}")

        # Extract result content
        if "result" in response:
            result = response["result"]
            if "content" in result and len(result["content"]) > 0:
                content_item = result["content"][0]
                if isinstance(content_item, dict):
                    if "text" in content_item:
                        return content_item["text"]
                    elif "data" in content_item:
                        return content_item["data"]
                return content_item
            return result

        return None

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
