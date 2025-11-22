"""FastMCP proxy server with middleware integration."""

import asyncio
import json
import os
import subprocess
import sys
import types
from typing import Any, Dict, Optional, Union

import httpx
from fastmcp import FastMCP

from cite_before_act.approval import ApprovalManager
from cite_before_act.debug import debug_log
from cite_before_act.detection import DetectionEngine
from cite_before_act.explain import ExplainEngine
from cite_before_act.local_approval import LocalApproval
from cite_before_act.middleware import Middleware
from cite_before_act.slack.client import SlackClient
from cite_before_act.slack.handlers import SlackHandler
from config.settings import Settings

# Optional platform imports
try:
    from cite_before_act.webex.client import WebexClient
    from cite_before_act.webex.handlers import WebexHandler
except ImportError:
    WebexClient = None
    WebexHandler = None

try:
    from cite_before_act.teams.client import TeamsClient
    from cite_before_act.teams.handlers import TeamsHandler
    from cite_before_act.teams.adapter import create_teams_adapter
except ImportError:
    TeamsClient = None
    TeamsHandler = None
    create_teams_adapter = None

# MCP Protocol Version
# Default to 2025-06-18 (latest as of implementation)
# Will be updated from negotiated version in initialize response
MCP_PROTOCOL_VERSION = "2025-06-18"


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
        self.upstream_http_client: Optional[httpx.AsyncClient] = None
        self.upstream_messages_url: Optional[str] = None  # For SSE transport
        self.upstream_sse_stream: Optional[httpx.AsyncClient] = None  # SSE event stream
        self.upstream_pending_responses: Dict[int, asyncio.Future] = {}  # Request ID -> Future for SSE
        self.upstream_sse_task: Optional[asyncio.Task] = None  # Background task for SSE events
        self.upstream_tools: Dict[str, Dict[str, Any]] = {}
        self._request_id = 3  # Start after init and list_tools
        self.mcp_protocol_version: str = MCP_PROTOCOL_VERSION  # Negotiated protocol version

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
                print("✅ Slack client initialized", file=sys.stderr)
            except Exception as e:
                print(f"Warning: Failed to initialize Slack client: {e}", file=sys.stderr)
                print("Falling back to local approval", file=sys.stderr)
                slack_configured = False

        # Webex integration (optional)
        webex_client = None
        webex_handler = None
        webex_configured = False
        if self.settings.enable_webex and self.settings.webex and WebexClient:
            try:
                webex_client = WebexClient(
                    access_token=self.settings.webex.token,
                    room_id=self.settings.webex.room_id,
                    person_email=self.settings.webex.person_email,
                )
                webex_handler = WebexHandler(access_token=self.settings.webex.token)
                webex_configured = True
                print("✅ Webex client initialized", file=sys.stderr)
            except Exception as e:
                print(f"Warning: Failed to initialize Webex client: {e}", file=sys.stderr)
                print("Webex approval will not be available", file=sys.stderr)
                webex_configured = False
        elif self.settings.enable_webex:
            if not WebexClient:
                print("Warning: Webex enabled but webexteamssdk not installed. Install with: pip install webexteamssdk", file=sys.stderr)
            elif not self.settings.webex:
                print("Warning: Webex enabled but not configured. Set WEBEX_BOT_TOKEN and WEBEX_ROOM_ID or WEBEX_PERSON_EMAIL.", file=sys.stderr)

        # Teams integration (optional)
        teams_client = None
        teams_handler = None
        teams_configured = False
        if self.settings.enable_teams and self.settings.teams and TeamsClient and create_teams_adapter:
            try:
                teams_adapter = create_teams_adapter(
                    app_id=self.settings.teams.app_id,
                    app_password=self.settings.teams.app_password,
                )
                teams_client = TeamsClient(
                    adapter=teams_adapter,
                    service_url=self.settings.teams.service_url,
                    conversation_id=self.settings.teams.conversation_id,
                    tenant_id=self.settings.teams.tenant_id,
                )
                teams_handler = TeamsHandler()
                teams_configured = True
                print("✅ Teams client initialized", file=sys.stderr)
            except Exception as e:
                print(f"Warning: Failed to initialize Teams client: {e}", file=sys.stderr)
                print("Teams approval will not be available", file=sys.stderr)
                teams_configured = False
        elif self.settings.enable_teams:
            if not TeamsClient:
                print("Warning: Teams enabled but botbuilder packages not installed. Install with: pip install botbuilder-core botframework-connector", file=sys.stderr)
            elif not self.settings.teams:
                print("Warning: Teams enabled but not configured. Set TEAMS_APP_ID and TEAMS_APP_PASSWORD.", file=sys.stderr)

        # Local approval configuration
        # Enable local approval to work in parallel with platform integrations
        # This provides multiple approval methods simultaneously:
        # - Platform notifications (Slack/Webex/Teams if configured)
        # - Native OS dialogs (macOS/Windows) - uses osascript/PowerShell
        # - File-based approval (all platforms) - always shown in logs
        local_approval = None
        any_platform_configured = slack_configured or webex_configured or teams_configured
        should_use_local = self.settings.use_local_approval or not any_platform_configured
        if should_use_local:
            # Use native dialogs on macOS/Windows, file-based on Linux
            # Native dialogs use osascript (macOS) or PowerShell (Windows)
            # These work even in stdio MCP mode because they run as separate processes
            # If any platform is configured, disable native dialogs but keep file-based logging
            use_native = self.settings.use_gui_approval
            if any_platform_configured:
                # When any platform is enabled, skip native popup but keep CLI logging
                use_native = False
            local_approval = LocalApproval(
                use_native_dialog=use_native,
                use_file_based=True,  # Always show file-based instructions in logs
            )

        # Approval manager
        approval_manager = ApprovalManager(
            slack_client=slack_client,
            slack_handler=slack_handler,
            webex_client=webex_client,
            webex_handler=webex_handler,
            teams_client=teams_client,
            teams_handler=teams_handler,
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
                    "protocolVersion": self.mcp_protocol_version,
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

            # Extract negotiated protocol version from response
            if "result" in init_response and "protocolVersion" in init_response["result"]:
                self.mcp_protocol_version = init_response["result"]["protocolVersion"]
                debug_log("Negotiated MCP protocol version: {}", self.mcp_protocol_version)

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
            # HTTP/SSE transport for remote MCP servers
            actual_transport = upstream_config.transport
            # Only use SSE if explicitly configured
            use_sse = actual_transport == "sse"
            is_github = "githubcopilot.com" in upstream_config.url
            
            debug_log("Connecting to upstream server: transport={}, url={}, use_sse={}, is_github={}", 
                     actual_transport, upstream_config.url, use_sse, is_github)
            debug_log("Upstream headers: {}", list(upstream_config.headers.keys()) if upstream_config.headers else "none")
            
            if use_sse:
                # SSE transport: Proper implementation for MCP SSE servers
                # 1. Open SSE connection (GET) to receive events
                # 2. Send requests via POST (try base URL first, then /messages)
                # 3. Parse SSE events and match to requests
                
                base_url = upstream_config.url.rstrip("/")
                # Try base URL first, fallback to /messages if needed
                messages_url = base_url  # Will try base URL first
                sse_url = base_url  # SSE events come from base URL
                
                # Build headers for SSE and POST requests
                auth_headers = upstream_config.headers.copy()
                post_headers = {
                    "Content-Type": "application/json",
                    "MCP-Protocol-Version": self.mcp_protocol_version,  # Required by MCP spec
                    **auth_headers,
                }
                sse_headers = {
                    "Accept": "text/event-stream",
                    "Cache-Control": "no-cache",
                    "MCP-Protocol-Version": self.mcp_protocol_version,  # Required by MCP spec
                    **auth_headers,
                }
                
                # Create HTTP client for POST requests
                self.upstream_http_client = httpx.AsyncClient(
                    timeout=httpx.Timeout(30.0, connect=10.0),
                )
                
                # Create separate client for SSE stream (needs longer timeout)
                self.upstream_sse_stream = httpx.AsyncClient(
                    timeout=httpx.Timeout(None, connect=10.0),  # No read timeout for SSE
                )
                
                # Store messages URL
                self.upstream_messages_url = messages_url
                
                # Start SSE event reader in background
                self.upstream_sse_task = asyncio.create_task(
                    self._read_sse_events(sse_url, sse_headers)
                )
                
                # Initialize MCP connection via POST to /messages
                init_request = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": self.mcp_protocol_version,
                        "capabilities": {},
                        "clientInfo": {"name": "cite-before-act-proxy", "version": "0.1.0"},
                    },
                }
                
                # For SSE, send requests via POST and wait for responses via SSE stream
                # Send initialize request
                init_future = asyncio.Future()
                self.upstream_pending_responses[1] = init_future
                
                try:
                    # Try POST to base URL first
                    try:
                        await self.upstream_http_client.post(
                            messages_url,
                            json=init_request,
                            headers=post_headers,
                        )
                    except httpx.HTTPStatusError as e:
                        # If 404/400, try /messages endpoint
                        if e.response.status_code in (400, 404) and messages_url == base_url:
                            debug_log("Base URL failed, trying /messages endpoint")
                            messages_url = f"{base_url}/messages"
                            self.upstream_messages_url = messages_url
                            await self.upstream_http_client.post(
                                messages_url,
                                json=init_request,
                                headers=post_headers,
                            )
                        else:
                            raise
                    
                    # Wait for response via SSE (with timeout)
                    init_response = await asyncio.wait_for(init_future, timeout=30.0)
                except asyncio.TimeoutError:
                    raise RuntimeError("Timeout waiting for initialize response from SSE server")
                except httpx.HTTPError as e:
                    error_msg = f"Failed to send initialize request: {e}"
                    if hasattr(e, 'response') and e.response is not None:
                        error_msg += f"\nStatus: {e.response.status_code}"
                        error_msg += f"\nResponse: {e.response.text[:500]}"
                    raise RuntimeError(error_msg)
                finally:
                    self.upstream_pending_responses.pop(1, None)
                
                if "error" in init_response:
                    raise RuntimeError(f"Upstream server initialization failed: {init_response['error']}")
                
                # Extract negotiated protocol version from response
                if "result" in init_response and "protocolVersion" in init_response["result"]:
                    self.mcp_protocol_version = init_response["result"]["protocolVersion"]
                    debug_log("Negotiated MCP protocol version: {}", self.mcp_protocol_version)
                
                # Send initialized notification (fire and forget)
                initialized_notification = {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                }
                try:
                    await self.upstream_http_client.post(
                        messages_url,
                        json=initialized_notification,
                        headers=post_headers,
                    )
                except httpx.HTTPError:
                    # Notification failures are non-fatal
                    pass
                
                # List tools from upstream server
                list_tools_request = {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list",
                    "params": {},
                }
                
                tools_future = asyncio.Future()
                self.upstream_pending_responses[2] = tools_future
                
                try:
                    await self.upstream_http_client.post(
                        messages_url,
                        json=list_tools_request,
                        headers=post_headers,
                    )
                    tools_response = await asyncio.wait_for(tools_future, timeout=30.0)
                except asyncio.TimeoutError:
                    raise RuntimeError("Timeout waiting for tools/list response from SSE server")
                except httpx.HTTPError as e:
                    raise RuntimeError(f"Failed to list tools from upstream server: {e}")
                finally:
                    self.upstream_pending_responses.pop(2, None)
                
                if "result" in tools_response and "tools" in tools_response["result"]:
                    for tool in tools_response["result"]["tools"]:
                        self.upstream_tools[tool["name"]] = {
                            "name": tool["name"],
                            "description": tool.get("description", ""),
                            "inputSchema": tool.get("inputSchema", {}),
                        }
            else:
                # HTTP POST transport (for servers that support direct HTTP POST)
                # Build headers for HTTP client
                headers = {
                    "Content-Type": "application/json",
                    "MCP-Protocol-Version": self.mcp_protocol_version,  # Required by MCP spec
                    **upstream_config.headers,  # Add custom headers (e.g., Authorization)
                }
                
                # Preserve URL as-is (with or without trailing slash)
                # Some servers are sensitive to trailing slashes
                base_url = upstream_config.url
                
                # Create async HTTP client without base_url to have full control
                self.upstream_http_client = httpx.AsyncClient(
                    timeout=httpx.Timeout(30.0, connect=10.0),
                )
                
                # Store the full URL for requests
                self.upstream_messages_url = base_url
                
                # Initialize MCP connection
                init_request = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": self.mcp_protocol_version,
                        "capabilities": {},
                        "clientInfo": {"name": "cite-before-act-proxy", "version": "0.1.0"},
                    },
                }
                
                # Send initialize request to the exact URL provided
                debug_log("Sending HTTP POST initialize request to: {}", base_url)
                debug_log("Request headers: {}", {k: v[:20] + "..." if len(v) > 20 else v for k, v in headers.items()})
                try:
                    response = await self.upstream_http_client.post(
                        base_url,
                        json=init_request,
                        headers=headers,
                    )
                    response.raise_for_status()
                    init_response = response.json()
                    debug_log("HTTP POST initialize successful")
                except httpx.HTTPStatusError as e:
                    # Log detailed error information
                    error_msg = f"HTTP POST failed for upstream server (Status: {e.response.status_code})"
                    error_msg += f"\nURL: {base_url}"
                    if e.response is not None:
                        try:
                            error_body = e.response.text[:500]
                            if error_body:
                                error_msg += f"\nServer response: {error_body}"
                        except Exception:
                            pass
                    
                    # Check if Authorization header might be missing or malformed
                    auth_header = headers.get("Authorization", "")
                    debug_log("Authorization header value: {}", auth_header[:50] + "..." if len(auth_header) > 50 else auth_header)
                    
                    if not auth_header:
                        error_msg += f"\n\nERROR: Authorization header is completely missing!"
                        error_msg += f"\nMake sure UPSTREAM_HEADER_Authorization is set in your Claude Desktop config."
                    elif auth_header.startswith("Bearer ${input:"):
                        error_msg += f"\n\nERROR: Authorization header was NOT substituted by Claude Desktop!"
                        error_msg += f"\nCurrent value: {auth_header}"
                        error_msg += f"\n\nThis means Claude Desktop did not prompt for the token."
                        error_msg += f"\nPossible causes:"
                        error_msg += f"\n  1. The 'inputs' section might be in the wrong place (must be at top level)"
                        error_msg += f"\n  2. The input ID 'github_mcp_pat' doesn't match the reference in the env var"
                        error_msg += f"\n  3. Claude Desktop needs to be restarted after adding the inputs section"
                    elif not auth_header.startswith("Bearer "):
                        error_msg += f"\n\nWARNING: Authorization header format may be incorrect."
                        error_msg += f"\nExpected format: 'Bearer <token>'"
                        error_msg += f"\nCurrent value: {auth_header[:50]}..."
                    
                    debug_log("HTTP POST error: {}", error_msg)
                    raise RuntimeError(error_msg)
                except httpx.HTTPError as e:
                    error_msg = f"Failed to connect to upstream server: {e}"
                    if hasattr(e, 'response') and e.response is not None:
                        error_msg += f"\nStatus: {e.response.status_code}"
                        error_msg += f"\nResponse: {e.response.text[:500]}"
                    raise RuntimeError(error_msg)
                except json.JSONDecodeError as e:
                    raise RuntimeError(f"Invalid response from upstream server: {e}")
                
                if "error" in init_response:
                    raise RuntimeError(f"Upstream server initialization failed: {init_response['error']}")
                
                # Extract negotiated protocol version from response
                if "result" in init_response and "protocolVersion" in init_response["result"]:
                    self.mcp_protocol_version = init_response["result"]["protocolVersion"]
                    debug_log("Negotiated MCP protocol version: {}", self.mcp_protocol_version)
                
                # Send initialized notification
                initialized_notification = {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                }
                try:
                    await self.upstream_http_client.post(
                        base_url,
                        json=initialized_notification,
                        headers=headers,
                    )
                except httpx.HTTPError:
                    # Notification failures are non-fatal
                    pass
                
                # List tools from upstream server
                list_tools_request = {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list",
                    "params": {},
                }
                
                try:
                    response = await self.upstream_http_client.post(
                        base_url,
                        json=list_tools_request,
                        headers=headers,
                    )
                    response.raise_for_status()
                    tools_response = response.json()
                except httpx.HTTPError as e:
                    error_msg = f"Failed to list tools from upstream server: {e}"
                    if hasattr(e, 'response') and e.response is not None:
                        error_msg += f"\nStatus: {e.response.status_code}"
                        error_msg += f"\nResponse: {e.response.text[:500]}"
                    raise RuntimeError(error_msg)
                except json.JSONDecodeError as e:
                    raise RuntimeError(f"Invalid response from upstream server: {e}")
                
                if "result" in tools_response and "tools" in tools_response["result"]:
                    for tool in tools_response["result"]["tools"]:
                        self.upstream_tools[tool["name"]] = {
                            "name": tool["name"],
                            "description": tool.get("description", ""),
                            "inputSchema": tool.get("inputSchema", {}),
                        }
                
                self.upstream_messages_url = None  # Use base URL for HTTP POST
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
            debug_log("Tool '{}' schema - required: {}, properties: {}", 
                     tool_name, required_params, list(properties.keys()))
            
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
        # Debug: Log arguments being sent
        debug_log("Calling upstream tool '{}' with arguments: {}", tool_name, arguments)

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

        # Handle different transport types
        if self.upstream_process:
            # stdio transport
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
        elif self.upstream_http_client:
            # HTTP/SSE transport
            if self.upstream_sse_stream and self.upstream_messages_url:
                # SSE transport: Send POST to /messages, wait for response via SSE
                request_future = asyncio.Future()
                self.upstream_pending_responses[request_id] = request_future
                
                try:
                    # Build headers for POST request
                    post_headers = {
                        "Content-Type": "application/json",
                        "MCP-Protocol-Version": self.mcp_protocol_version,  # Required by MCP spec
                    }
                    if self.settings.upstream and self.settings.upstream.headers:
                        post_headers.update(self.settings.upstream.headers)
                    
                    # Send POST request to /messages
                    await self.upstream_http_client.post(
                        self.upstream_messages_url,
                        json=tool_request,
                        headers=post_headers,
                    )
                    # Wait for response via SSE (with timeout)
                    response = await asyncio.wait_for(request_future, timeout=60.0)
                except asyncio.TimeoutError:
                    raise RuntimeError(f"Timeout waiting for response to tool '{tool_name}' from SSE server")
                except httpx.HTTPError as e:
                    error_msg = f"HTTP request to upstream server failed: {e}"
                    if hasattr(e, 'response') and e.response is not None:
                        error_msg += f"\nStatus: {e.response.status_code}"
                        error_msg += f"\nResponse: {e.response.text[:500]}"
                    raise RuntimeError(error_msg)
                finally:
                    self.upstream_pending_responses.pop(request_id, None)
            else:
                # HTTP POST transport (direct response)
                request_url = self.upstream_messages_url if self.upstream_messages_url else ""
                request_headers = {
                    "Content-Type": "application/json",
                    "MCP-Protocol-Version": self.mcp_protocol_version,  # Required by MCP spec
                }
                # Add Authorization header if it was in the original config
                if self.settings.upstream and self.settings.upstream.headers:
                    request_headers.update(self.settings.upstream.headers)
                
                try:
                    http_response = await self.upstream_http_client.post(
                        request_url,
                        json=tool_request,
                        headers=request_headers,
                    )
                    http_response.raise_for_status()
                    response = http_response.json()
                except httpx.HTTPError as e:
                    error_msg = f"HTTP request to upstream server failed: {e}"
                    if hasattr(e, 'response') and e.response is not None:
                        error_msg += f"\nStatus: {e.response.status_code}"
                        error_msg += f"\nResponse: {e.response.text[:500]}"
                    raise RuntimeError(error_msg)
                except json.JSONDecodeError as e:
                    raise RuntimeError(f"Invalid JSON response from upstream server: {e}")
        else:
            raise RuntimeError("Upstream server not available")

        # Debug: Log response structure
        debug_log("Upstream tool '{}' response structure: {}", 
                 tool_name, json.dumps(response, indent=2)[:500])

        if "error" in response:
            raise RuntimeError(f"Upstream tool call failed: {response['error']}")

        # Pass through the entire result structure as-is
        # We're a proxy/wrapper - our job is approval interception, not response transformation
        # The upstream MCP server knows best how to format its responses
        if "result" in response:
            result = response["result"]
            
            # FastMCP expects tool handlers to return the content array directly
            # (it will wrap it in the MCP result format)
            # If result has content array, return it so all items are preserved
            if "content" in result and isinstance(result["content"], list):
                return result["content"]
            
            # Otherwise return the full result structure
            # FastMCP will handle it appropriately
            return result

        return None

    async def _read_sse_events(self, sse_url: str, sse_headers: Dict[str, str]) -> None:
        """Read SSE events from upstream server and match them to pending requests.
        
        Args:
            sse_url: URL to connect to for SSE events
            sse_headers: Headers to use for SSE connection
        """
        try:
            async with self.upstream_sse_stream.stream(
                "GET",
                sse_url,
                headers=sse_headers,
            ) as response:
                response.raise_for_status()
                
                # Buffer for incomplete SSE messages
                event_data = []
                
                async for line in response.aiter_lines():
                    # SSE format: lines starting with "data: " contain the payload
                    # Empty line indicates end of event
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix
                        event_data.append(data)
                    elif line == "" and event_data:
                        # Empty line indicates end of event, process accumulated data
                        # Join all data lines (SSE allows multi-line data)
                        buffer = "\n".join(event_data)
                        event_data = []
                        
                        if not buffer.strip():
                            continue
                        
                        try:
                            message = json.loads(buffer)
                            
                            # Check if this is a response to a pending request
                            if "id" in message:
                                request_id = message["id"]
                                if request_id in self.upstream_pending_responses:
                                    future = self.upstream_pending_responses[request_id]
                                    if not future.done():
                                        future.set_result(message)
                                        debug_log("Matched SSE response for request ID: {}", request_id)
                        except json.JSONDecodeError:
                            # Skip invalid JSON
                            debug_log("Invalid JSON in SSE event: {}", buffer[:200])
                    elif line.startswith(":"):
                        # Comment line, ignore
                        continue
                    elif line.startswith("event: "):
                        # Event type, can be ignored for now
                        continue
                    elif line.startswith("id: "):
                        # Event ID, can be ignored for now
                        continue
                    elif line.startswith("retry: "):
                        # Retry interval, can be ignored for now
                        continue
                            
        except asyncio.CancelledError:
            # Task was cancelled, clean up
            pass
        except Exception as e:
            debug_log("Error reading SSE events: {}", e)
            # Cancel all pending requests
            for future in self.upstream_pending_responses.values():
                if not future.done():
                    future.set_exception(RuntimeError(f"SSE connection error: {e}"))

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
