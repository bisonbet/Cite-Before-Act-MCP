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
git clone https://github.com/bisonbet/Cite-Before-Act-MCP.git
cd Cite-Before-Act-MCP
pip install -e .
```

### Step 3: Set Up Slack App

1. **Create a Slack App**: Go to https://api.slack.com/apps and create a new app
2. **Navigate to OAuth & Permissions**:
   - In the left-hand sidebar of your app's settings, click on **"OAuth & Permissions"**
3. **Add Bot Token Scopes**:
   - Scroll down to the **"Scopes"** section
   - Under **"Bot Token Scopes"**, click **"Add an OAuth Scope"**
   - Add the following scope:
     - `chat:write` - Send messages (required for sending approval requests with buttons)
4. **Install the App to Workspace**:
   - Scroll back up to the **"OAuth Tokens for Your Workspace"** section
   - Click **"Install to Workspace"** (or **"Reinstall to Workspace"** if already installed)
   - Authorize the app with the requested permissions
5. **Copy the Bot Token**:
   - After installation, copy the **"Bot User OAuth Token"** (starts with `xoxb-`)
   - This is the token you'll use in your `.env` file

**Note**: Interactive components (button clicks) don't require a separate OAuth scope. They work via webhook URLs configured in the "Interactive Components" section. For basic approval workflows, the `chat:write` scope is sufficient. If you want to receive button click responses via webhook, see the [Slack App Setup](#slack-app-setup) section below for webhook configuration.

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

## Configuring Claude Desktop

To use Cite-Before-Act MCP with Claude Desktop, you need to add the proxy server to Claude Desktop's MCP configuration.

### Step-by-Step Claude Desktop Setup

1. **Locate Claude Desktop Configuration File**:
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   - **Linux**: `~/.config/Claude/claude_desktop_config.json`

2. **Open the Configuration File**:
   - If the file doesn't exist, create it
   - Use any text editor to open it

3. **Add the Cite-Before-Act MCP Server**:
   - The file should be a JSON object with an `mcpServers` key
   - Add the following configuration:

   ```json
   {
     "mcpServers": {
       "cite-before-act": {
         "command": "python",
         "args": [
           "-m",
           "server.main",
           "--transport",
           "stdio"
         ],
         "env": {
           "SLACK_BOT_TOKEN": "xoxb-your-token-here",
           "SLACK_CHANNEL": "#approvals",
           "DETECTION_ALLOWLIST": "write_file,edit_file,create_directory,move_file,delete_file",
           "DETECTION_BLOCKLIST": "read_text_file,read_media_file,list_directory,get_file_info",
           "DETECTION_ENABLE_CONVENTION": "true",
           "DETECTION_ENABLE_METADATA": "true",
           "UPSTREAM_COMMAND": "npx",
           "UPSTREAM_ARGS": "-y,@modelcontextprotocol/server-filesystem,~/mcp-test-workspace",
           "UPSTREAM_TRANSPORT": "stdio",
           "APPROVAL_TIMEOUT_SECONDS": "300",
           "ENABLE_SLACK": "true"
         }
       }
     }
   }
   ```

   **Important Notes**:
   - Replace `xoxb-your-token-here` with your actual Slack bot token
   - Replace `#approvals` with your desired Slack channel (or use a channel ID)
   - Replace `~/mcp-test-workspace` with the path to your test directory (use absolute path if needed)
   - Make sure the `python` command in `command` points to the Python interpreter where you installed the package (you may need to use the full path, e.g., `/usr/local/bin/python3` or the path to your virtual environment's Python)

4. **Complete Example Configuration**:
   
   If you already have other MCP servers configured, your file might look like this:

   ```json
   {
     "mcpServers": {
       "cite-before-act": {
         "command": "python",
         "args": [
           "-m",
           "server.main",
           "--transport",
           "stdio"
         ],
         "env": {
           "SLACK_BOT_TOKEN": "xoxb-1234567890-1234567890123-AbCdEfGhIjKlMnOpQrStUvWx",
           "SLACK_CHANNEL": "#approvals",
           "DETECTION_ALLOWLIST": "write_file,edit_file,create_directory,move_file,delete_file",
           "DETECTION_BLOCKLIST": "read_text_file,read_media_file,list_directory,get_file_info",
           "DETECTION_ENABLE_CONVENTION": "true",
           "DETECTION_ENABLE_METADATA": "true",
           "UPSTREAM_COMMAND": "npx",
           "UPSTREAM_ARGS": "-y,@modelcontextprotocol/server-filesystem,/Users/yourname/mcp-test-workspace",
           "UPSTREAM_TRANSPORT": "stdio",
           "APPROVAL_TIMEOUT_SECONDS": "300",
           "ENABLE_SLACK": "true"
         }
       },
       "other-server": {
         "command": "other-command",
         "args": ["arg1", "arg2"]
       }
     }
   }
   ```

5. **Save the Configuration File**:
   - Save the file with the `.json` extension
   - Make sure the JSON is valid (no trailing commas, proper quotes, etc.)

6. **Restart Claude Desktop**:
   - Completely quit Claude Desktop (not just close the window)
   - Reopen Claude Desktop
   - The MCP server should now be available

7. **Verify the Connection**:
   - In Claude Desktop, you should see the Cite-Before-Act MCP server listed
   - The server will expose tools from the upstream filesystem server
   - You should also see an `explain` tool for generating previews

### Using Python from a Virtual Environment

If you installed the package in a virtual environment, use the full path to that Python:

```json
{
  "mcpServers": {
    "cite-before-act": {
      "command": "/path/to/venv/bin/python",
      "args": [
        "-m",
        "server.main",
        "--transport",
        "stdio"
      ],
      "env": {
        // ... your environment variables
      }
    }
  }
}
```

To find your virtual environment's Python path:
```bash
# If using venv
which python  # after activating the venv

# If using conda
conda info --envs  # then use the path shown
```

### Troubleshooting Claude Desktop Configuration

**Issue: MCP server not appearing in Claude Desktop**
- Verify the JSON file is valid (use a JSON validator)
- Check that the Python path is correct
- Ensure all dependencies are installed in that Python environment
- Check Claude Desktop's logs for error messages
- Make sure you completely restarted Claude Desktop (quit and reopen)

**Issue: "Command not found" errors**
- Use the full path to Python instead of just `python`
- Verify the Python environment has `cite-before-act-mcp` installed
- Check that `server.main` module can be imported: `python -m server.main --help`

**Issue: Environment variables not working**
- Make sure all environment variables are in the `env` object
- Use absolute paths for directory references
- Verify Slack token and channel are correct

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

To receive approval responses, you need to set up a Slack app with the proper permissions:

### OAuth Scopes Setup

1. **Create a Slack App**: Go to https://api.slack.com/apps and create a new app
2. **Navigate to OAuth & Permissions**:
   - In the left-hand sidebar of your app's settings, click on **"OAuth & Permissions"**
3. **Add Bot Token Scopes**:
   - Scroll down to the **"Scopes"** section
   - Under **"Bot Token Scopes"**, click **"Add an OAuth Scope"**
   - Add the following scope:
     - `chat:write` - Send messages (required for sending approval requests with interactive buttons)
4. **Install to Workspace**:
   - Scroll back up to the **"OAuth Tokens for Your Workspace"** section
   - Click **"Install to Workspace"** (or **"Reinstall to Workspace"** if you've added new scopes)
   - Follow the prompts to authorize the app
5. **Copy the Bot Token**:
   - After installation, copy the **"Bot User OAuth Token"** (starts with `xoxb-`)
   - Save this token - you'll need it for your `.env` file

### Interactive Components Setup (Optional - for Webhook Responses)

If you want to receive button click responses via webhook (instead of polling), configure Interactive Components:

1. **Navigate to Interactive Components**:
   - In the left-hand sidebar, click on **"Interactive Components"**
2. **Enable Interactive Components**:
   - Toggle **"Interactivity"** to **On**
3. **Set Request URL**:
   - Enter your webhook URL (e.g., `https://your-server.com/slack/interactive`)
   - This URL must be publicly accessible (use ngrok for local testing)
   - Click **"Save Changes"**
4. **Test the Webhook**:
   - See `examples/slack_webhook_example.py` for a Flask example
   - Use ngrok to expose your local server: `ngrok http 3000`

**Note**: Interactive components don't require a separate OAuth scope. The `chat:write` scope is sufficient to send messages with buttons. Button clicks are handled via the webhook URL you configure, not through OAuth scopes.

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

**For Claude Desktop Users**: You don't need to use these JSON commands directly. Simply ask Claude in natural language (e.g., "create a file called test.txt"). The JSON below shows what happens internally - it's for reference only.

**For Developers/Advanced Users**: The JSON format shows the internal tool call structure. If you're using MCP Inspector or another tool, you can use these JSON structures directly.

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

#### Complete End-to-End Test with Claude Desktop

**Prerequisites**: Make sure you've completed the [Claude Desktop configuration](#configuring-claude-desktop) above.

1. **Verify Claude Desktop is configured**:
   - Open Claude Desktop
   - The Cite-Before-Act MCP server should be listed and connected
   - You should see tools from the filesystem server available

2. **Test non-mutating operation** (should work immediately):
   - In Claude Desktop, type: "List the contents of ~/mcp-test-workspace"
   - Claude will use the `list_directory` tool
   - Should return directory listing **immediately without** requiring Slack approval
   - This confirms non-mutating operations pass through correctly

3. **Test file creation** (should require approval):
   - In Claude Desktop, type: "Create a file called test.txt in ~/mcp-test-workspace with the content 'Hello, World! This is a test file.'"
   - Claude will attempt to use the `write_file` tool
   - **Check your Slack channel** (#approvals or your configured channel) - you should see an approval request with:
     - Tool name: `write_file`
     - Description of what will happen
     - Arguments that will be passed
     - Two buttons: **"✅ Approve"** and **"❌ Reject"**
   - Click the **"✅ Approve"** button in Slack
   - Return to Claude Desktop - the file should now be created
   - Claude should confirm the file was created successfully

4. **Verify the file was created**:
   - In Claude Desktop, type: "Read the file ~/mcp-test-workspace/test.txt"
   - Claude will use the `read_text_file` tool
   - Should return the file contents **immediately without** requiring approval
   - Verify the content matches "Hello, World! This is a test file."

5. **Test file deletion** (should require approval):
   - In Claude Desktop, type: "Delete the file ~/mcp-test-workspace/test.txt"
   - Claude will attempt to use the `delete_file` tool
   - **Check Slack** for another approval request
   - Review the preview showing the file will be permanently deleted
   - Click **"✅ Approve"** in Slack
   - Return to Claude Desktop - the file should be deleted
   - Claude should confirm the deletion

6. **Verify deletion**:
   - In Claude Desktop, type: "List the files in ~/mcp-test-workspace"
   - The `test.txt` file should no longer appear in the listing
   - Or try: "Read ~/mcp-test-workspace/test.txt" - it should indicate the file doesn't exist

### What You Should See

**In Claude Desktop:**
- Non-mutating operations (read, list) work immediately
- Mutating operations (write, delete) show a message indicating approval is required
- After approval in Slack, the operation completes

**In Slack:**
- Approval requests appear as formatted messages with tool details
- Interactive buttons for Approve/Reject
- Status updates when actions are processed

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
- Check that the `chat:write` OAuth scope is added in "OAuth & Permissions"
- If using webhooks for button responses, verify Interactive Components is configured with a valid Request URL

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
