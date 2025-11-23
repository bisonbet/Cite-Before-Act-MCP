# Architecture

This document explains the architecture and internal structure of Cite-Before-Act MCP.

## High-Level Architecture

```
Client → Cite-Before-Act Proxy → Middleware → Detection → Explain → Approval → Upstream Server
                                    ↓
                              (if mutating)
                                    ↓
                          Multi-Method Approval
                          (Native Dialog + Slack + File)
                                    ↓
                              Execute or Reject
```

## Component Overview

### Proxy Server
- Entry point for MCP clients (Claude Desktop, etc.)
- Handles MCP protocol communication
- Routes requests to middleware layer
- Supports multiple transports: stdio, HTTP, SSE

### Middleware
- Intercepts all tool calls before execution
- Coordinates detection, explanation, and approval
- Manages tool call lifecycle
- Located in: `cite_before_act/middleware.py`

### Detection Engine
- Identifies mutating vs. read-only operations
- Multi-strategy detection (allowlist, blocklist, convention, metadata)
- Configurable per server
- Located in: `cite_before_act/detection.py`

### Explain Engine
- Generates human-readable previews of tool actions
- Extracts key information from tool arguments
- Creates natural language descriptions
- Located in: `cite_before_act/explain.py`

### Approval Manager
- Coordinates multiple approval methods
- Handles timeouts and cancellations
- Manages approval state
- Located in: `cite_before_act/approval.py`

### Local Approval
- Native OS dialogs (macOS/Windows)
- File-based CLI logging
- Always available, no configuration needed
- Located in: `cite_before_act/local_approval.py`

### Slack Integration
- Sends approval requests to Slack
- Supports interactive buttons via webhooks
- Optional, requires configuration
- Located in: `cite_before_act/slack/`

## Project Structure

```
cite_before_act_mcp/
├── cite_before_act/      # Core library
│   ├── detection.py      # Mutating tool detection
│   ├── explain.py        # Natural language previews
│   ├── approval.py       # Approval workflow management
│   ├── local_approval.py # Local approval (native dialogs + file-based)
│   ├── middleware.py     # Main middleware logic
│   └── slack/            # Slack integration
│       ├── client.py     # Slack API client
│       └── webhook.py    # Webhook server components
├── server/               # Standalone proxy server
│   ├── proxy.py         # FastMCP proxy implementation
│   └── main.py          # Entry point
├── config/              # Configuration management
│   └── settings.py      # Environment variable handling
├── examples/            # Usage examples
│   ├── library_usage.py
│   ├── standalone_server.py
│   └── unified_webhook_server.py
├── tests/               # Test suite
└── docs/                # Documentation (you are here!)
```

## Request Flow

### Non-Mutating Operation

1. Client sends tool call request
2. Proxy receives request
3. Middleware intercepts call
4. Detection engine identifies as read-only
5. Proxy forwards to upstream server immediately
6. Response returned to client

### Mutating Operation

1. Client sends tool call request
2. Proxy receives request
3. Middleware intercepts call
4. Detection engine identifies as mutating
5. Explain engine generates preview
6. Approval manager requests approval via:
   - Native OS dialog (if enabled)
   - Slack message (if configured)
   - File-based instructions (always)
7. User approves/rejects
8. If approved: Proxy forwards to upstream server
9. If rejected: Error returned to client
10. Response (or error) returned to client

## Configuration System

### Two-Tier Configuration

1. **`.env` file** - Global settings and secrets
   - Loaded by `config/settings.py`
   - Applies to all wrapped servers
   - Contains sensitive tokens

2. **Claude Desktop config** - Per-server settings
   - Environment variables in `mcpServers.env`
   - Specific to each upstream server
   - Overrides `.env` settings

### Precedence Order

1. Claude Desktop `mcpServers.env` (highest)
2. `.env` file (lower)
3. Defaults in code (lowest)

## Transport Modes

### stdio (Standard Input/Output)
- Default mode for Claude Desktop
- Subprocess communication
- Process spawned by client

### HTTP
- REST API communication
- Suitable for remote servers
- Supports custom headers for auth

### SSE (Server-Sent Events)
- Modern streaming protocol
- Long-lived connections
- Used by some remote MCP servers

## Dependencies

### Core
- **FastMCP** - MCP server framework and proxy capabilities
- **python-dotenv** - Environment variable management
- **asyncio** - Asynchronous operation support

### Slack Integration (Optional)
- **slack-sdk** - Slack API client
- **Flask** - Webhook server (optional for interactive buttons)

## Next Steps

- [Development Guide](development.md) - Contributing to the project
- [Advanced Usage](advanced-usage.md) - Custom integrations
