# Cite-Before-Act MCP

An MCP middleware server that requires explicit approval for state-mutating tool calls. For any tool that mutates state (send email, charge card, delete file), it forces a "citation-first" dry-run with an LLM-readable preview; only on explicit approval does it execute.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Quick Start](#quick-start)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Configuration](#configuration)
- [Setup for Claude Desktop](#setup-for-claude-desktop)
  - [Step-by-Step Configuration](#step-by-step-configuration)
  - [Troubleshooting](#troubleshooting-claude-desktop)
- [Testing the Setup](#testing-the-setup)
  - [End-to-End Test Workflow](#end-to-end-test-workflow)
  - [Available Operations](#available-operations)
- [Approval Methods](#approval-methods)
  - [Local Approval (Default)](#local-approval-default)
  - [Slack Integration (Optional)](#slack-integration-optional)
  - [Multiple Methods Working Together](#multiple-methods-working-together)
- [Configuration Reference](#configuration-reference)
  - [Environment Variables](#environment-variables)
  - [Detection Settings](#detection-settings)
  - [Upstream Server](#upstream-server)
- [Advanced Usage](#advanced-usage)
  - [As a Library](#as-a-library)
  - [Standalone Server](#standalone-server)
- [Architecture](#architecture)
- [Development](#development)
- [License](#license)

## Overview

Cite-Before-Act MCP implements the "human-in-the-loop" safety pattern for MCP servers. It acts as a proxy that:

1. **Intercepts** all tool calls before execution
2. **Detects** mutating operations using multiple strategies
3. **Generates** human-readable previews of what would happen
4. **Requests** approval via multiple methods (native dialogs, Slack, file-based)
5. **Executes** only after explicit approval

This provides a standardized "dry-run → approval → execute" workflow that other MCP servers can leverage.

## Features

- **Multi-Strategy Detection**: Identifies mutating tools via allowlist/blocklist, naming conventions, and metadata analysis
- **Natural Language Previews**: Generates human-readable descriptions of tool actions
- **Multiple Approval Methods**: Native OS dialogs (macOS/Windows), Slack integration, and file-based approval
- **Works Out of the Box**: Local approval requires no configuration
- **FastMCP Based**: Built on FastMCP for easy integration and proxy capabilities
- **Configurable**: Flexible configuration via environment variables
- **Protocol-Agnostic**: Can wrap any MCP server regardless of implementation language

## Quick Start

### Prerequisites

- Python 3.10 or higher
- Node.js 18+ and npm (for the filesystem MCP server)
- (Optional) Slack workspace with a bot token

### Installation

```bash
git clone https://github.com/bisonbet/Cite-Before-Act-MCP.git
cd Cite-Before-Act-MCP
pip install -e .
```

### Configuration

**The system works immediately with local approval - no configuration needed!**

For optional Slack integration or custom settings:

1. Copy the example configuration:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and uncomment the variables you need:
   ```bash
   # For Slack integration (optional)
   SLACK_BOT_TOKEN=xoxb-your-token-here
   SLACK_CHANNEL=#approvals

   # For upstream server (required for proxy mode)
   UPSTREAM_COMMAND=npx
   UPSTREAM_ARGS=-y,@modelcontextprotocol/server-filesystem,/absolute/path/to/directory
   ```

See [`.env.example`](.env.example) for all available options.

## Setup for Claude Desktop

### Step-by-Step Configuration

**1. Create Test Directory**

```bash
mkdir -p ~/mcp-test-workspace
cd ~/mcp-test-workspace && pwd  # Copy this absolute path
```

**2. Locate Claude Desktop Config File**

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

**3. Add Configuration**

**Quick Setup:** Copy the configuration from [`claude_desktop_config.example.json`](claude_desktop_config.example.json) and paste into your `claude_desktop_config.json`, then edit as needed.

**Manual Setup:** Add this configuration (replace paths and tokens):

```json
{
  "mcpServers": {
    "cite-before-act": {
      "command": "python",
      "args": ["-m", "server.main", "--transport", "stdio"],
      "env": {
        "UPSTREAM_COMMAND": "npx",
        "UPSTREAM_ARGS": "-y,@modelcontextprotocol/server-filesystem,/Users/yourname/mcp-test-workspace",
        "UPSTREAM_TRANSPORT": "stdio",
        "USE_LOCAL_APPROVAL": "true",
        "USE_NATIVE_DIALOG": "true"
      }
    }
  }
}
```

**Optional Slack Configuration:** Add these to the `env` object:
```json
"SLACK_BOT_TOKEN": "xoxb-your-token-here",
"SLACK_CHANNEL": "#approvals",
"ENABLE_SLACK": "true"
```

**4. Update Paths**

- Replace `/Users/yourname/mcp-test-workspace` with the absolute path from step 1
- If using a virtual environment, use the full path to Python (e.g., `/path/to/venv/bin/python`)

**5. Restart Claude Desktop**

- Completely quit Claude Desktop
- Reopen the application
- Verify the server is connected and tools are available

### Troubleshooting Claude Desktop

**Server not appearing:**
- Verify JSON syntax is valid
- Check Python path is correct
- Ensure dependencies are installed
- Review Claude Desktop logs for errors

**Only seeing `explain` tool (no filesystem tools):**
1. Verify Node.js is installed: `node --version`
2. Test upstream server: `npx -y @modelcontextprotocol/server-filesystem /path/to/test/directory`
3. Use absolute paths (not `~` or relative paths)
4. Ensure test directory exists

**Slack channel errors:**
- **Private channels**: Use `approvals` (no `#`), invite bot with `/invite @YourBotName`
- **Public channels**: Use `#approvals` (with `#`)
- Verify bot has required OAuth scopes (`chat:write`, `channels:read`)

## Testing the Setup

### End-to-End Test Workflow

**1. Test Non-Mutating Operation (Immediate)**

In Claude Desktop, type:
```
List the contents of ~/mcp-test-workspace
```

Expected: Returns directory listing immediately without approval.

**2. Test File Creation (Requires Approval)**

In Claude Desktop, type:
```
Create a file called test.txt in ~/mcp-test-workspace with the content 'Hello, World!'
```

Expected:
- **macOS/Windows**: Native dialog appears with approval buttons
- **All platforms**: File-based instructions in Claude Desktop logs
- **If Slack configured**: Approval request sent to Slack channel

Click **Approve** in the dialog or Slack, or approve via file:
```bash
echo "approved" > /tmp/cite-before-act-approval-{id}.json
```

**3. Test File Reading (Immediate)**

In Claude Desktop, type:
```
Read the file ~/mcp-test-workspace/test.txt
```

Expected: Returns file contents immediately without approval.

**4. Test File Deletion (Requires Approval)**

In Claude Desktop, type:
```
Delete the file ~/mcp-test-workspace/test.txt
```

Expected: Approval request appears (native dialog, Slack, or file-based).

### Available Operations

**Mutating Operations (Require Approval):**
- `write_file` - Create/write files
- `edit_file` - Edit file content
- `create_directory` - Create directories
- `move_file` - Move/rename files
- `delete_file` - Delete files
- `delete_directory` - Delete directories

**Non-Mutating Operations (Immediate):**
- `read_text_file` - Read file content
- `read_media_file` - Read media files
- `list_directory` - List directory contents
- `get_file_info` - Get file metadata
- `search_files` - Search for files

## Approval Methods

### Local Approval (Default)

**Works out of the box - no configuration needed!**

**Native OS Dialogs:**
- **macOS**: Uses AppleScript (`osascript`) - no special permissions needed
- **Windows**: Uses PowerShell MessageBox
- **Linux**: File-based only (no native dialog available)

**File-Based Approval:**
- Instructions always printed to Claude Desktop logs
- Works on all platforms
- Approve: `echo "approved" > /tmp/cite-before-act-approval-{id}.json`
- Reject: `echo "rejected" > /tmp/cite-before-act-approval-{id}.json`

### Slack Integration (Optional)

**Setup Steps:**

1. **Create Slack App** at https://api.slack.com/apps
2. **Add OAuth Scopes** (OAuth & Permissions):
   - `chat:write` - Send messages (required)
   - `channels:read` - List public channels
   - `groups:read` - List private channels (if using private channels)
   - `channels:join` - Join public channels
3. **Install to Workspace** and copy the Bot User OAuth Token
4. **Invite Bot to Channel**:
   - Private channels: `/invite @YourBotName` (required)
   - Public channels: Auto-joins with `channels:join` scope
5. **Configure Environment**:
   ```bash
   SLACK_BOT_TOKEN=xoxb-your-token-here
   SLACK_CHANNEL=#approvals  # Public: #name, Private: name (no #)
   ```

**Interactive Buttons (Optional):**

To enable Approve/Reject buttons in Slack:

1. Run webhook server: `python examples/slack_webhook_example.py`
2. Expose with ngrok: `ngrok http 3000`
3. Configure in Slack: Interactive Components → Request URL → `https://your-ngrok-url.ngrok.io/slack/interactive`

Without webhooks, you'll still receive Slack notifications but must approve via local methods.

### Multiple Methods Working Together

**All enabled approval methods work simultaneously in parallel:**

1. **Native OS dialog** appears (macOS/Windows)
2. **Slack notification** sent (if configured)
3. **File-based instructions** printed to logs (always)

**Any method can approve** - whichever responds first wins!

**Configuration:**
```bash
USE_LOCAL_APPROVAL=true       # Default: true
USE_NATIVE_DIALOG=true        # Default: true (macOS/Windows only)
ENABLE_SLACK=true             # Default: true (requires SLACK_BOT_TOKEN)
APPROVAL_TIMEOUT_SECONDS=300  # Default: 300 (5 minutes)
```

## Configuration Reference

### Environment Variables

See [`.env.example`](.env.example) for complete documentation. Key variables:

**Approval Settings:**
```bash
APPROVAL_TIMEOUT_SECONDS=300    # Timeout in seconds
USE_LOCAL_APPROVAL=true         # Enable local approval
USE_NATIVE_DIALOG=true          # Use native OS dialogs
ENABLE_SLACK=true               # Enable Slack (requires token)
```

**Slack Configuration:**
```bash
SLACK_BOT_TOKEN=xoxb-...        # Bot token (required for Slack)
SLACK_CHANNEL=#approvals        # Channel name or ID
SLACK_USER_ID=U1234567890       # For DMs instead of channel
```

### Detection Settings

```bash
# Explicit allowlist (always require approval)
DETECTION_ALLOWLIST=write_file,delete_file,send_email

# Explicit blocklist (never require approval)
DETECTION_BLOCKLIST=read_file,list_directory,get_info

# Enable detection strategies
DETECTION_ENABLE_CONVENTION=true   # Detect by naming (write_, delete_, etc.)
DETECTION_ENABLE_METADATA=true     # Detect by tool description
```

**Detection Strategies:**
1. **Allowlist**: Explicitly listed tools always require approval
2. **Blocklist**: Explicitly listed tools never require approval
3. **Convention-Based**: Detects common prefixes/suffixes (`write_`, `delete_`, `send_`, etc.)
4. **Metadata-Based**: Analyzes tool descriptions for keywords

All strategies use OR logic - if any strategy detects mutation, approval is required.

### Upstream Server

**stdio transport (subprocess):**
```bash
UPSTREAM_COMMAND=npx
UPSTREAM_ARGS=-y,@modelcontextprotocol/server-filesystem,/absolute/path
UPSTREAM_TRANSPORT=stdio
```

**HTTP transport (remote server):**
```bash
UPSTREAM_URL=http://localhost:3010
UPSTREAM_TRANSPORT=http
```

**SSE transport (server-sent events):**
```bash
UPSTREAM_URL=http://localhost:3010
UPSTREAM_TRANSPORT=sse
```

## Advanced Usage

### As a Library

```python
from cite_before_act import DetectionEngine, ExplainEngine, ApprovalManager, Middleware
from cite_before_act.slack import SlackClient

# Initialize components
detection = DetectionEngine(allowlist=["write_file", "delete_file"])
explain = ExplainEngine()
slack_client = SlackClient(token="xoxb-...", channel="#approvals")
approval_manager = ApprovalManager(slack_client=slack_client)

middleware = Middleware(
    detection_engine=detection,
    explain_engine=explain,
    approval_manager=approval_manager,
    upstream_tool_call=your_tool_call_function,
)

# Intercept tool calls
result = await middleware.call_tool(
    tool_name="write_file",
    arguments={"path": "/tmp/test.txt", "content": "Hello"},
)
```

See `examples/library_usage.py` for complete examples.

### Standalone Server

Run the proxy server directly:

```bash
# stdio transport (default)
python -m server.main --transport stdio

# HTTP transport
python -m server.main --transport http --host 0.0.0.0 --port 8000

# SSE transport
python -m server.main --transport sse --host 0.0.0.0 --port 8000
```

## Architecture

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

**Project Structure:**
```
cite_before_act_mcp/
├── cite_before_act/      # Core library
│   ├── detection.py      # Mutating tool detection
│   ├── explain.py        # Natural language previews
│   ├── approval.py       # Approval workflow management
│   ├── local_approval.py # Local approval (native dialogs + file-based)
│   ├── middleware.py     # Main middleware logic
│   └── slack/            # Slack integration
├── server/               # Standalone proxy server
│   ├── proxy.py         # FastMCP proxy implementation
│   └── main.py          # Entry point
├── config/              # Configuration management
├── examples/            # Usage examples
└── tests/               # Test suite
```

## Development

**Setup:**
```bash
pip install -e ".[dev]"
```

**Run Tests:**
```bash
pytest
```

**Code Formatting:**
```bash
black .
ruff check .
```

## License

AGPL-3.0 - See LICENSE file for details.

## Contributing

Contributions welcome! Please open an issue or pull request on GitHub.

## Acknowledgments

- Built with [FastMCP](https://github.com/jlowin/fastmcp)
- Tested with [Official MCP Filesystem Server](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem)
