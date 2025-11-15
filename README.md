# Cite-Before-Act MCP

An MCP middleware server that requires explicit approval for state-mutating tool calls. For any tool that mutates state (send email, charge card, delete file), it forces a "citation-first" dry-run with an LLM-readable preview; only on explicit approval does it execute.

## Overview

Cite-Before-Act MCP implements the "human-in-the-loop" safety pattern for MCP servers. It acts as a proxy that:

1. **Intercepts** all tool calls before execution
2. **Detects** mutating operations using multiple strategies
3. **Generates** human-readable previews of what would happen
4. **Requests** approval via Slack before executing
5. **Executes** only after explicit approval

This provides a standardized "dry-run → approval → execute" workflow that other MCP servers can leverage.

## Features

- **Multi-Strategy Detection**: Identifies mutating tools via allowlist/blocklist, naming conventions, and metadata analysis
- **Natural Language Previews**: Generates human-readable descriptions of tool actions
- **Slack Integration**: Sends approval requests with interactive buttons for approve/reject
- **FastMCP Based**: Built on FastMCP for easy integration and proxy capabilities
- **Configurable**: Flexible configuration via environment variables or config files
- **Protocol-Agnostic**: Can wrap any MCP server regardless of implementation language

## Quick Start Guide

### Step 1: Prerequisites

- Python 3.10 or higher
- Node.js 18+ and npm (for the filesystem MCP server)
- Slack workspace with a bot token

### Step 2: Install Cite-Before-Act MCP

```bash
git clone https://github.com/yourusername/Cite-Before-Act-MCP.git
cd Cite-Before-Act-MCP
pip install -e .
```

### Step 3: Set Up Slack App

1. Go to https://api.slack.com/apps and create a new app
2. Add the following **Bot Token Scopes**:
   - `chat:write` - Send messages
   - `interactive:write` - Handle button clicks
3. Install the app to your workspace
4. Copy the **Bot User OAuth Token** (starts with `xoxb-`)

### Step 4: Configure Environment

Create a `.env` file in the project root:

```bash
# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-token-here
SLACK_CHANNEL=#approvals

# Detection Configuration
DETECTION_ALLOWLIST=write_file,edit_file,create_directory,move_file,delete_file
DETECTION_BLOCKLIST=read_text_file,read_media_file,list_directory,get_file_info
DETECTION_ENABLE_CONVENTION=true
DETECTION_ENABLE_METADATA=true

# Upstream Server (Official MCP Filesystem Server)
UPSTREAM_COMMAND=npx
UPSTREAM_ARGS=-y,@modelcontextprotocol/server-filesystem
UPSTREAM_TRANSPORT=stdio

# Approval Settings
APPROVAL_TIMEOUT_SECONDS=300
ENABLE_SLACK=true
```

### Step 5: Set Up Filesystem MCP Server

The official MCP Filesystem Server requires configuration of allowed directories. Create a test directory:

```bash
# Create a test directory for file operations
mkdir -p ~/mcp-test-workspace
```

The filesystem server will need to know which directories it can access. When using `npx`, you can pass directory arguments, but the exact method depends on how the server is invoked. For testing purposes, we'll configure it to use a specific directory.

### Step 6: Run the Proxy Server

```bash
python -m server.main --transport stdio
```

The server is now ready to intercept tool calls and require approval for mutating operations!

## Installation

### Install Dependencies

```bash
pip install -r requirements.txt
```

## Configuration

Configuration is done via environment variables or a `.env` file.

### Slack Configuration

```bash
# Required: Slack bot token (get from https://api.slack.com/apps)
SLACK_BOT_TOKEN=xoxb-your-token-here

# Optional: Channel to send approval requests (channel name or ID)
SLACK_CHANNEL=#approvals

# Optional: User ID for direct messages instead of channel
# SLACK_USER_ID=U1234567890
```

### Detection Configuration

```bash
# Optional: Explicit list of mutating tool names (comma-separated)
DETECTION_ALLOWLIST=write_file,delete_file,send_email,charge_card

# Optional: Explicit list of non-mutating tools (everything else is mutating)
DETECTION_BLOCKLIST=read_file,list_directory,get_file_info

# Enable/disable detection strategies (default: true)
DETECTION_ENABLE_CONVENTION=true
DETECTION_ENABLE_METADATA=true
```

### Upstream Server Configuration

The proxy needs to know how to connect to the upstream MCP server.

**Option 1: stdio transport (run as subprocess)**

```bash
UPSTREAM_COMMAND=npx
UPSTREAM_ARGS=-y,@modelcontextprotocol/server-filesystem
UPSTREAM_TRANSPORT=stdio
```

**Option 2: HTTP transport (remote server)**

```bash
UPSTREAM_URL=http://localhost:3010
UPSTREAM_TRANSPORT=http
```

### Approval Settings

```bash
# Default timeout for approval requests (seconds)
APPROVAL_TIMEOUT_SECONDS=300

# Enable/disable Slack integration
ENABLE_SLACK=true
```

### Complete Example `.env` File

```bash
# Slack
SLACK_BOT_TOKEN=xoxb-your-token-here
SLACK_CHANNEL=#approvals

# Detection
DETECTION_ALLOWLIST=write_file,edit_file,create_directory,move_file,delete_file
DETECTION_BLOCKLIST=read_text_file,read_media_file,list_directory,get_file_info
DETECTION_ENABLE_CONVENTION=true
DETECTION_ENABLE_METADATA=true

# Upstream Server (Official MCP Filesystem Server)
UPSTREAM_COMMAND=npx
UPSTREAM_ARGS=-y,@modelcontextprotocol/server-filesystem
UPSTREAM_TRANSPORT=stdio

# Approval
APPROVAL_TIMEOUT_SECONDS=300
ENABLE_SLACK=true
```

## Usage

### Standalone Server

Run the proxy server to wrap an upstream MCP server:

```bash
# stdio transport (default)
python -m server.main --transport stdio

# HTTP transport
python -m server.main --transport http --host 0.0.0.0 --port 8000

# SSE transport
python -m server.main --transport sse --host 0.0.0.0 --port 8000
```

### As a Library

Use the middleware components directly in your code:

```python
from cite_before_act import DetectionEngine, ExplainEngine, ApprovalManager, Middleware
from cite_before_act.slack import SlackClient, SlackHandler

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

# Use middleware to intercept tool calls
result = await middleware.call_tool(
    tool_name="write_file",
    arguments={"path": "/tmp/test.txt", "content": "Hello"},
)
```

See `examples/library_usage.py` for a complete example.

## Slack App Setup

To receive approval responses, you need to set up a Slack app:

1. **Create a Slack App**: Go to https://api.slack.com/apps and create a new app
2. **Add Bot Token Scopes**:
   - `chat:write` - Send messages
   - `commands` - Handle slash commands (optional)
   - `interactive:write` - Handle button clicks
3. **Install to Workspace**: Install the app to your workspace
4. **Get Bot Token**: Copy the bot token (starts with `xoxb-`)
5. **Set Up Interactive Components** (optional, for webhook):
   - Add a Request URL (e.g., `https://your-server.com/slack/interactive`)
   - See `examples/slack_webhook_example.py` for a Flask example

## Testing with Official MCP Filesystem Server

The official MCP Filesystem Server is an ideal test target because it provides both mutating and non-mutating operations.

### Filesystem Server Setup

1. **Install Node.js and npm** (if not already installed):
   ```bash
   # Check if installed
   node --version
   npm --version
   ```

2. **Create a test workspace directory**:
   ```bash
   mkdir -p ~/mcp-test-workspace
   cd ~/mcp-test-workspace
   ```

3. **Configure the upstream server in your `.env`**:
   ```bash
   UPSTREAM_COMMAND=npx
   UPSTREAM_ARGS=-y,@modelcontextprotocol/server-filesystem,~/mcp-test-workspace
   UPSTREAM_TRANSPORT=stdio
   ```
   
   Note: The filesystem server requires at least one allowed directory. The directory path should be passed as an argument after the package name.

4. **Start the proxy server**:
   ```bash
   python -m server.main --transport stdio
   ```

### Available Operations

**Mutating Operations** (require approval):
- `write_file` - Writes content to a file
- `edit_file` - Edits file content  
- `create_directory` - Creates a directory
- `move_file` - Moves/renames files
- `delete_file` - Deletes a file
- `delete_directory` - Deletes a directory

**Non-Mutating Operations** (pass through without approval):
- `read_text_file` - Reads file content
- `read_media_file` - Reads media file content
- `list_directory` - Lists directory contents
- `get_file_info` - Gets file metadata
- `search_files` - Searches for files using glob patterns

### Test Commands

Once your proxy server is running and connected to an MCP client (like Claude Desktop or another MCP client), you can test the approval workflow with these operations.

**Note:** The JSON format below shows the internal tool call structure. When using an MCP client, you'll typically interact through the client's interface (e.g., asking Claude to "create a file called test.txt" or using the MCP Inspector tool interface).

#### 1. Create a File (Requires Approval)

```json
{
  "tool": "write_file",
  "arguments": {
    "path": "~/mcp-test-workspace/test.txt",
    "content": "Hello, World! This is a test file."
  }
}
```

**Expected Behavior:**
- Middleware detects `write_file` as mutating (via allowlist or convention)
- Generates preview: "This will create or write to a file or resource with parameters: path='~/mcp-test-workspace/test.txt', content='Hello, World! This is a test file.'. Impact: will create or modify file at ~/mcp-test-workspace/test.txt"
- Sends approval request to Slack channel
- Waits for approval before executing
- If approved: file is created
- If rejected: `PermissionError` is raised

#### 2. Read a File (No Approval Required)

```json
{
  "tool": "read_text_file",
  "arguments": {
    "path": "~/mcp-test-workspace/test.txt"
  }
}
```

**Expected Behavior:**
- Middleware detects `read_text_file` as non-mutating (via blocklist)
- Passes through directly to upstream server
- Returns file contents immediately

#### 3. List Directory (No Approval Required)

```json
{
  "tool": "list_directory",
  "arguments": {
    "path": "~/mcp-test-workspace"
  }
}
```

**Expected Behavior:**
- Middleware detects `list_directory` as non-mutating
- Passes through directly
- Returns directory listing

#### 4. Delete a File (Requires Approval)

```json
{
  "tool": "delete_file",
  "arguments": {
    "path": "~/mcp-test-workspace/test.txt"
  }
}
```

**Expected Behavior:**
- Middleware detects `delete_file` as mutating
- Generates preview: "This will delete or remove a file or resource with parameters: path='~/mcp-test-workspace/test.txt'. Impact: will permanently delete ~/mcp-test-workspace/test.txt"
- Sends approval request to Slack
- If approved: file is deleted
- If rejected: `PermissionError` is raised

### Testing Workflow Example

#### Complete End-to-End Test

1. **Start the proxy server**:
   ```bash
   python -m server.main --transport stdio
   ```

2. **Configure your MCP client** (e.g., Claude Desktop) to use the proxy server:
   - Edit your MCP configuration file (location varies by client)
   - Point to the proxy server instead of the filesystem server directly
   - Example configuration:
     ```json
     {
       "mcpServers": {
         "cite-before-act": {
           "command": "python",
           "args": ["-m", "server.main", "--transport", "stdio"]
         }
       }
     }
     ```

3. **Test non-mutating operation** (should work immediately):
   - In your MCP client, ask to "list the contents of ~/mcp-test-workspace"
   - Or use tool: `list_directory` with path `~/mcp-test-workspace`
   - Should return directory listing **without** requiring Slack approval

4. **Test file creation** (should require approval):
   - In your MCP client, ask to "create a file called test.txt in ~/mcp-test-workspace with content 'Hello, World!'"
   - Or use tool: `write_file` with path `~/mcp-test-workspace/test.txt` and content `Hello, World!`
   - **Check your Slack channel** - you should see an approval request
   - Click the **"✅ Approve"** button in Slack
   - File should be created after approval

5. **Verify the file was created**:
   - Ask to "read the file ~/mcp-test-workspace/test.txt"
   - Or use tool: `read_text_file` with path `~/mcp-test-workspace/test.txt`
   - Should return the file contents **without** requiring approval
   - Verify the content matches what you wrote

6. **Test file deletion** (should require approval):
   - Ask to "delete the file ~/mcp-test-workspace/test.txt"
   - Or use tool: `delete_file` with path `~/mcp-test-workspace/test.txt`
   - **Check Slack** for another approval request
   - Click **"✅ Approve"** in Slack
   - File should be deleted after approval

7. **Verify deletion**:
   - Try to read the file again - it should not exist
   - Or list the directory to confirm the file is gone

### Using MCP Inspector (Alternative Testing)

You can also test using the [MCP Inspector](https://github.com/modelcontextprotocol/inspector):

```bash
# Install MCP Inspector
npm install -g @modelcontextprotocol/inspector

# Run inspector pointing to your proxy server
# (Configuration depends on how you're running the proxy)
```

### Troubleshooting

**Issue: Approval requests not appearing in Slack**
- Verify `SLACK_BOT_TOKEN` is correct and starts with `xoxb-`
- Check that the bot is installed to your workspace
- Verify `SLACK_CHANNEL` exists and the bot has access
- Check bot token scopes include `chat:write` and `interactive:write`

**Issue: Filesystem operations failing**
- Verify the test directory exists: `~/mcp-test-workspace`
- Check that the directory path in `UPSTREAM_ARGS` is correct
- Ensure the filesystem server has permission to access the directory

**Issue: Non-mutating operations requiring approval**
- Check your `DETECTION_BLOCKLIST` includes the tool name
- Verify `DETECTION_ENABLE_CONVENTION` and `DETECTION_ENABLE_METADATA` settings
- Review tool names match your allowlist/blocklist exactly

## Detection Strategies

The detection engine uses multiple strategies to identify mutating tools:

1. **Allowlist**: Explicit list of mutating tool names
2. **Blocklist**: Explicit list of non-mutating tools (everything else is mutating)
3. **Convention-Based**: Detects common prefixes (`write_`, `delete_`, `send_`, etc.) and suffixes
4. **Metadata-Based**: Analyzes tool descriptions for keywords like "mutate", "delete", "create", etc.

All strategies are combined with OR logic - if any strategy detects a tool as mutating, it requires approval.

## Architecture

```
Client → Cite-Before-Act Proxy → Middleware → Detection → Explain → Approval → Upstream Server
                                    ↓
                              (if mutating)
                                    ↓
                              Slack Approval
                                    ↓
                              Execute or Reject
```

## Project Structure

```
cite_before_act_mcp/
├── cite_before_act/      # Core library
│   ├── detection.py      # Mutating tool detection
│   ├── explain.py        # Natural language previews
│   ├── approval.py       # Approval workflow management
│   ├── middleware.py     # Main middleware logic
│   └── slack/            # Slack integration
├── server/                # Standalone proxy server
│   ├── proxy.py          # FastMCP proxy implementation
│   └── main.py           # Entry point
├── config/                # Configuration management
├── examples/              # Usage examples
└── tests/                 # Test suite
```

## Development

### Setup Development Environment

```bash
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest
```

### Code Formatting

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
