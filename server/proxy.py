"""FastMCP proxy server with middleware integration."""

import asyncio
import json
import os
import subprocess
import sys
import types
from typing import Any, Dict, Optional, Union

from fastmcp import FastMCP

from cite_before_act.approval import ApprovalManager
from cite_before_act.detection import DetectionEngine
from cite_before_act.explain import ExplainEngine
from cite_before_act.local_approval import LocalApproval
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

        # Slack integration (optional)
        slack_client = None
        slack_handler = None
        slack_configured = False
        if self.settings.enable_slack and self.settings.slack:
            try:
                slack_client = SlackClient(
                    token=self.settings.slack.token,
                    channel=self.settings.slack.channel,
                    user_id=self.settings.slack.user_id,
                )
                slack_handler = SlackHandler(client=slack_client.client)
                slack_configured = True
            except Exception as e:
                print(f"Warning: Failed to initialize Slack client: {e}", file=sys.stderr)
                print("Falling back to local approval", file=sys.stderr)
                slack_configured = False

        # Local approval configuration
        # Enable local approval to work in parallel with Slack
        # This provides multiple approval methods simultaneously:
        # - Slack notifications (if configured)
        # - Native OS dialogs (macOS/Windows) - uses osascript/PowerShell
        # - File-based approval (all platforms) - always shown in logs
        local_approval = None
        should_use_local = self.settings.use_local_approval or not slack_configured
        if should_use_local:
            # Use native dialogs on macOS/Windows, file-based on Linux
            # Native dialogs use osascript (macOS) or PowerShell (Windows)
            # These work even in stdio MCP mode because they run as separate processes
            # If Slack is configured, disable native dialogs but keep file-based logging
            use_native = os.getenv("USE_NATIVE_DIALOG", "true").lower() == "true"
            if slack_configured:
                # When Slack is enabled, skip native popup but keep CLI logging
                use_native = False
            local_approval = LocalApproval(
                use_native_dialog=use_native,
                use_file_based=True,  # Always show file-based instructions in logs
            )

        # Approval manager
        approval_manager = ApprovalManager(
            slack_client=slack_client,
            slack_handler=slack_handler,
            local_approval=local_approval,
            default_timeout_seconds=self.settings.approval_timeout_seconds,
            use_local_fallback=True,  # Always use local as fallback
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
            # Prepare environment variables for upstream server
            # Start with current environment
            upstream_env = os.environ.copy()
            
            # Pass through any environment variables that upstream servers might need
            # GitHub MCP server needs GITHUB_PERSONAL_ACCESS_TOKEN
            github_token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
            if github_token:
                upstream_env["GITHUB_PERSONAL_ACCESS_TOKEN"] = github_token
            
            # Pass through any other GITHUB_* variables that might be needed
            for key, value in os.environ.items():
                if key.startswith("GITHUB_"):
                    upstream_env[key] = value
            
            # Start upstream server as subprocess
            self.upstream_process = subprocess.Popen(
                [upstream_config.command] + upstream_config.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0,
                env=upstream_env,
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
            if not response_line:
                # Check if process has exited
                if self.upstream_process.poll() is not None:
                    # Process has exited, try to read stderr
                    stderr_output = ""
                    try:
                        stderr_output = self.upstream_process.stderr.read(1024) if self.upstream_process.stderr else ""
                    except Exception:
                        pass
                    
                    error_msg = f"Upstream server process exited with code {self.upstream_process.returncode}"
                    if stderr_output:
                        error_msg += f"\nStderr output: {stderr_output}"
                    raise RuntimeError(error_msg)
                else:
                    raise RuntimeError("Upstream server did not respond to initialize request")
            
            try:
                init_response = json.loads(response_line.strip())
            except json.JSONDecodeError as e:
                # Check if process has exited
                stderr_output = ""
                if self.upstream_process.poll() is not None:
                    try:
                        stderr_output = self.upstream_process.stderr.read(1024) if self.upstream_process.stderr else ""
                    except Exception:
                        pass
                
                error_msg = f"Failed to parse upstream server response: {e}\nReceived: {response_line[:200]}"
                if stderr_output:
                    error_msg += f"\nStderr output: {stderr_output}"
                raise RuntimeError(error_msg)
            
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
            required_params = set(input_schema.get("required", []))
            param_names = list(properties.keys())
            
            # Debug: Print schema info for troubleshooting
            import sys
            print(f"[DEBUG] Tool '{tool_name}' schema - required: {required_params}, properties: {list(properties.keys())}", file=sys.stderr)
            
            # Capture variables in closure (before creating function)
            name = tool_name
            desc = tool_info.get("description", "")
            schema = input_schema
            middleware_ref = self.middleware
            tools_ref = self.upstream_tools
            
            # Create a function with explicit parameters
            # FastMCP requires explicit parameters, not **kwargs
            # Make optional parameters have default values of None
            if param_names:
                # Build function signature with optional parameters having defaults
                param_defs = []
                for param_name in param_names:
                    prop = properties.get(param_name, {})
                    param_type = prop.get("type", "string")
                    # Map JSON schema types to Python types
                    if param_type == "integer" or param_type == "number":
                        type_hint = "int" if param_type == "integer" else "float"
                    elif param_type == "boolean":
                        type_hint = "bool"
                    elif param_type == "array":
                        type_hint = "list"
                    elif param_type == "object":
                        type_hint = "dict"
                    else:
                        type_hint = "str"
                    
                    # Make parameter optional if not in required list
                    if param_name not in required_params:
                        param_defs.append(f"{param_name}: Optional[{type_hint}] = None")
                    else:
                        param_defs.append(f"{param_name}: {type_hint}")
                
                params_str = ", ".join(param_defs)
                # Build code to collect and convert parameters into dict
                # We need to convert string parameters to their correct types based on schema
                collect_code = "arguments = {}\n"
                # Convert and add all parameters (required and optional)
                for p in param_names:
                    prop = properties.get(p, {})
                    param_type = prop.get("type", "string")
                    var_name = p
                    
                    # Build conversion code based on type
                    if param_type == "integer":
                        # Convert to int (handle string "1" -> int 1)
                        if p in required_params:
                            collect_code += f"    arguments['{p}'] = int({var_name}) if isinstance({var_name}, str) else {var_name}\n"
                        else:
                            collect_code += f"    if {var_name} is not None:\n"
                            collect_code += f"        arguments['{p}'] = int({var_name}) if isinstance({var_name}, str) else {var_name}\n"
                    elif param_type == "number":
                        # Convert to float (handle string "1.0" -> float 1.0)
                        if p in required_params:
                            collect_code += f"    arguments['{p}'] = float({var_name}) if isinstance({var_name}, str) else {var_name}\n"
                        else:
                            collect_code += f"    if {var_name} is not None:\n"
                            collect_code += f"        arguments['{p}'] = float({var_name}) if isinstance({var_name}, str) else {var_name}\n"
                    elif param_type == "boolean":
                        # Convert to bool (handle string "true"/"false" -> bool)
                        if p in required_params:
                            collect_code += f"    if isinstance({var_name}, str):\n"
                            collect_code += f"        arguments['{p}'] = {var_name}.lower() in ('true', '1', 'yes')\n"
                            collect_code += f"    else:\n"
                            collect_code += f"        arguments['{p}'] = bool({var_name})\n"
                        else:
                            collect_code += f"    if {var_name} is not None:\n"
                            collect_code += f"        if isinstance({var_name}, str):\n"
                            collect_code += f"            arguments['{p}'] = {var_name}.lower() in ('true', '1', 'yes')\n"
                            collect_code += f"        else:\n"
                            collect_code += f"            arguments['{p}'] = bool({var_name})\n"
                    else:
                        # String, array, object - pass through as-is
                        # For optional string parameters, filter out empty strings
                        if p in required_params:
                            collect_code += f"    arguments['{p}'] = {var_name}\n"
                        else:
                            collect_code += f"    if {var_name} is not None and {var_name} != '':\n"
                            collect_code += f"        arguments['{p}'] = {var_name}\n"
            else:
                params_str = ""
                collect_code = "arguments = {}"
            
            # Create function using a factory that properly captures closure
            # The key is to make sure variables are captured from the function parameters
            def create_handler(
                tool_name_inner: str,
                tool_desc_inner: str,
                tool_schema_inner: dict,
                middleware_inner: Middleware,
                tools_dict: dict,
                param_list: list,
                collect_code_inner: str,
            ):
                # Build the function body - variables are in create_handler's scope
                if param_list:
                    params_str_inner = ", ".join(param_list)
                else:
                    params_str_inner = ""
                
                # Create function code that references variables from create_handler's scope
                # These will be captured in the closure when we exec
                func_code = f"""async def handler({params_str_inner}):
    \"\"\"{tool_desc_inner}\"\"\"
    {collect_code_inner}
    # Reference variables from outer scope (create_handler parameters)
    if not middleware_inner:
        raise RuntimeError("Middleware not initialized")
    tool_desc = tools_dict.get(tool_name_inner, {{}}).get("description", "")
    return await middleware_inner.call_tool(
        tool_name=tool_name_inner,
        arguments=arguments,
        tool_description=tool_desc,
        tool_schema=tool_schema_inner,
    )
"""
                # Execute in local namespace
                # The key is to put variables in globals so the function can access them
                # When exec creates a function, it looks in globals for free variables
                globals_dict = {
                    "asyncio": asyncio,
                    "Optional": Optional,
                    "middleware_inner": middleware_inner,
                    "tools_dict": tools_dict,
                    "tool_name_inner": tool_name_inner,
                    "tool_schema_inner": tool_schema_inner,
                }
                local_vars = {}
                exec(func_code, globals_dict, local_vars)
                handler_func = local_vars["handler"]
                
                # The function should now have access to the variables via globals
                return handler_func
            
            # Create the handler with proper closure
            handler = create_handler(
                name,
                desc,
                schema,
                middleware_ref,
                tools_ref,
                param_names,
                collect_code,
            )
            
            # Register with FastMCP
            # Use 'name' (captured variable) instead of 'tool_name' (loop variable) to avoid closure issues
            self.mcp.tool(name=name, description=desc)(handler)

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

        # Debug: Log arguments being sent
        import sys
        print(f"[DEBUG] Calling upstream tool '{tool_name}' with arguments: {arguments}", file=sys.stderr)

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

        # Debug: Log response structure
        import sys
        print(f"[DEBUG] Upstream tool '{tool_name}' response structure: {json.dumps(response, indent=2)[:500]}", file=sys.stderr)

        if "error" in response:
            raise RuntimeError(f"Upstream tool call failed: {response['error']}")

        # Extract result content
        if "result" in response:
            result = response["result"]
            if "content" in result and len(result["content"]) > 0:
                content_items = result["content"]
                
                # Prioritize resource content (actual file/data content)
                # over status messages
                resource_content = None
                text_content = []
                
                for item in content_items:
                    if isinstance(item, dict):
                        # Check for resource type (actual content)
                        if item.get("type") == "resource" and "resource" in item:
                            resource = item["resource"]
                            # Extract text from resource if available
                            if "text" in resource:
                                resource_content = resource["text"]
                            elif "data" in resource:
                                resource_content = resource["data"]
                            elif "uri" in resource:
                                # Resource URI - might be useful for reference
                                resource_content = f"Resource: {resource['uri']}"
                        # Check for direct text content
                        elif "text" in item:
                            text_content.append(item["text"])
                        elif "data" in item:
                            text_content.append(item["data"])
                        else:
                            # Fallback: string representation
                            text_content.append(str(item))
                    else:
                        text_content.append(str(item))
                
                # Return resource content if available (actual file/data)
                if resource_content:
                    return resource_content
                
                # Otherwise, return combined text content
                if text_content:
                    if len(text_content) == 1:
                        return text_content[0]
                    # Join multiple text items with newlines
                    return "\n".join(text_content)
                
                # Fallback: return first item as-is
                return content_items[0]
            
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
