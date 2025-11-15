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
- **Multiple Approval Methods**: Native OS dialogs (macOS/Windows), Slack integration, and file-based CLI logging
- **Smart Method Selection**: Automatically disables native popups when Slack is enabled (prevents duplicates)
- **Works Out of the Box**: Local approval requires no configuration
- **FastMCP Based**: Built on FastMCP for easy integration and proxy capabilities
- **Configurable**: Flexible configuration via environment variables
- **Protocol-Agnostic**: Can wrap any MCP server regardless of implementation language

## Quick Start

### Option 1: Automated Setup (Recommended)

Run the interactive setup wizard to configure everything automatically:

```bash
git clone https://github.com/bisonbet/Cite-Before-Act-MCP.git
cd Cite-Before-Act-MCP
python3 setup_wizard.py
```

The setup wizard will:
- ✅ Create a Python virtual environment
- ✅ Install all dependencies
- ✅ Guide you through Slack configuration (optional)
- ✅ Set up ngrok for webhooks (optional)
- ✅ Generate Claude Desktop configuration
- ✅ Create convenient startup scripts

**Perfect for:** First-time setup, getting started quickly, automatic configuration

### Adding Additional MCP Servers

Once you have a working setup, you can re-run the setup wizard to add additional upstream MCP servers:

```bash
python3 setup_wizard.py
```

When the wizard detects an existing setup, it will offer two options:
1. **Full Setup** - Reconfigure everything from scratch
2. **Add New MCP Server** - Add another upstream server configuration (recommended)

The "Add New MCP Server" option will:
- ✅ Skip venv creation and dependency installation (uses existing setup)
- ✅ Skip Slack configuration (uses existing settings from `.env`)
- ✅ Only configure the new upstream MCP server
- ✅ Merge the new configuration with your existing Claude Desktop config
- ✅ Generate unique server names (e.g., `cite-before-act-github`, `cite-before-act-filesystem`)

This allows you to have multiple MCP servers wrapped by Cite-Before-Act MCP, each with its own configuration in Claude Desktop.

### Option 2: Manual Setup

#### Prerequisites

- Python 3.10 or higher
- Node.js 18+ and npm (for the filesystem MCP server)
- (Optional) Slack workspace with a bot token
- (Optional) ngrok account for webhook hosting

#### Installation

```bash
git clone https://github.com/bisonbet/Cite-Before-Act-MCP.git
cd Cite-Before-Act-MCP
pip install -e .
```

#### Configuration

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

**Perfect for:** Advanced users, custom configurations, understanding the internals

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
- **If Slack NOT configured**: Native dialog appears (macOS/Windows) + file-based instructions in logs
- **If Slack configured**: Approval request sent to Slack channel + file-based instructions in logs (no popup)

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
- **Note**: Native dialogs are automatically disabled when Slack is enabled (see below)

**File-Based Approval (CLI Logging):**
- Instructions always printed to Claude Desktop logs (stderr)
- Works on all platforms
- Always enabled, even when Slack is configured
- Provides CLI backup for all approval methods
- Approve: `echo "approved" > /tmp/cite-before-act-approval-{id}.json`
- Reject: `echo "rejected" > /tmp/cite-before-act-approval-{id}.json`

### Slack Integration (Optional)

**Important Behavior:**
- **When Slack is enabled**: Native OS popup dialogs are automatically disabled
- **CLI logging still works**: File-based approval instructions are always printed to logs as a backup
- This prevents duplicate approval requests (Slack + popup) while maintaining CLI visibility

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
   ENABLE_SLACK=true
   ```

**Interactive Buttons (Optional):**

To enable Approve/Reject buttons in Slack, you need to run a webhook server. See the [Slack Webhook Security](#slack-webhook-security) section below for detailed setup.

**Quick Setup:**
1. Run webhook server: `python examples/slack_webhook_server.py`
2. Expose with ngrok: `ngrok http 3000`
3. Configure in Slack: Interactive Components → Request URL → `https://your-ngrok-url.ngrok.io/slack/interactive`

Without webhooks, you'll still receive Slack notifications but must approve via file-based method or Slack reactions.

### Slack Webhook Security

The webhook server (`examples/slack_webhook_server.py`) supports two security modes, depending on your hosting approach:

#### Security Mode Comparison

| Security Mode | Best For | HMAC in App | Rate Limiting | Use Case |
|--------------|----------|-------------|---------------|----------|
| **Web Service Hosted** | ngrok with verification | ❌ Optional | ❌ No | ngrok handles verification at tunnel level |
| **Self-Hosted** | Direct internet exposure | ✅ Required | ✅ Yes | Your server validates requests |

#### Web Service Hosted Mode (ngrok with Signature Verification)

**Security Features:**
- ✅ Approval ID validation (prevents path traversal attacks)
- ✅ ngrok signature verification (at tunnel level)
- ✅ Configurable debug mode
- ❌ No application-level HMAC verification (ngrok handles it)
- ❌ No rate limiting (rely on ngrok)

**When to use:** Production or development with ngrok (free tier: 500 verifications/month, unlimited on Pro/Enterprise)

**Why this is production-ready:** ngrok validates Slack signatures before requests reach your app, providing the same security as application-level HMAC verification.

**Setup with ngrok Signature Verification:**

```bash
# 1. Get your Slack signing secret
# Go to: https://api.slack.com/apps → Your App → Basic Information → Signing Secret

# 2. Create ngrok traffic policy file: ngrok-slack-policy.yml
cat > ngrok-slack-policy.yml <<EOF
on_http_request:
  - actions:
      - type: "webhook-verification"
        config:
          provider: "slack"
          secret: "YOUR_SLACK_SIGNING_SECRET_HERE"
EOF

# 3. Set environment variables
export SLACK_BOT_TOKEN=xoxb-your-token-here
export SECURITY_MODE=local  # ngrok handles verification

# 4. Run the webhook server
python examples/slack_webhook_server.py

# 5. In another terminal, start ngrok with traffic policy
ngrok http 3000 --traffic-policy-file ngrok-slack-policy.yml

# 6. Configure in Slack
# Go to: https://api.slack.com/apps → Your App → Interactivity & Shortcuts
# Set Request URL: https://your-ngrok-url.ngrok.io/slack/interactive
```

**How ngrok verification works:** ngrok validates Slack's signature at the tunnel level before forwarding requests to your app. Invalid requests are blocked automatically.

**Free tier limitation:** 500 signature verifications per month. Upgrade to ngrok Pro or Enterprise for unlimited verifications.

**Alternative (basic setup without verification):**
```bash
export SLACK_BOT_TOKEN=xoxb-your-token-here
python examples/slack_webhook_server.py
ngrok http 3000  # No verification - use only for quick testing
```

⚠️ **Without ngrok verification or HMAC verification, anyone with your ngrok URL can send fake approval requests.**

#### Self-Hosted Mode (Direct Internet Exposure)

**Security Features:**
- ✅ Slack HMAC-SHA256 signature verification (in application)
- ✅ Approval ID validation (prevents path traversal)
- ✅ Rate limiting (configurable, default: 60 requests/minute)
- ✅ Input validation (prevents JSON bomb attacks)
- ✅ Sanitized error messages (prevents information disclosure)
- ✅ Replay attack prevention (5-minute timestamp window)
- ✅ Debug mode disabled by default

**When to use:** Self-hosted servers directly exposed to internet (no ngrok tunnel), or when you need application-level rate limiting

**Why HMAC in the app?** When your server is directly accessible from the internet (not behind ngrok), you need to validate Slack signatures at the application level. This cryptographically verifies that requests actually come from Slack, preventing anyone from sending fake approval requests.

**Setup:**
```bash
# 1. Get your Slack signing secret
# Go to: https://api.slack.com/apps → Your App → Basic Information → Signing Secret

# 2. Set environment variables
export SLACK_BOT_TOKEN=xoxb-your-token-here
export SLACK_SIGNING_SECRET=your-signing-secret-here
export SECURITY_MODE=production

# 3. Run the webhook server
python examples/slack_webhook_server.py

# 4. Deploy your server
# - Cloud providers: Use your provider's deployment method (AWS, GCP, Azure, etc.)
# - VPS: Run server on your VPS with process manager (systemd, supervisor, etc.)
# - Ensure server is accessible via HTTPS (required by Slack)
# - Example URL: https://your-domain.com or https://your-server-ip:3000

# 5. Configure in Slack
# Go to: https://api.slack.com/apps → Your App → Interactivity & Shortcuts
# Set Request URL: https://your-domain.com/slack/interactive
```

**How HMAC verification works:** Your application validates Slack's cryptographic signature on every request. Only requests with valid signatures (proving they came from Slack) are processed. Invalid requests are rejected with a 401 error.

#### Configuration Reference

| Environment Variable | Web Service (ngrok) | Self-Hosted | Default | Description |
|---------------------|---------------------|-------------|---------|-------------|
| `SLACK_BOT_TOKEN` | Required | Required | - | Your Slack bot token |
| `SECURITY_MODE` | `local` | `production` | `local` | Security mode |
| `SLACK_SIGNING_SECRET` | For ngrok policy* | Required | - | Slack signing secret |
| `PORT` | Optional | Optional | `3000` | Webhook server port |
| `DEBUG` | Optional | Not recommended | `false` | Flask debug mode |
| `RATE_LIMIT_MAX_REQUESTS` | N/A | Optional | `60` | Max requests per window |
| `RATE_LIMIT_WINDOW_SECONDS` | N/A | Optional | `60` | Rate limit window (seconds) |

\* For web service hosted (ngrok): Secret goes in ngrok traffic policy file, not environment variable

#### Security Best Practices

**For All Deployments:**
1. **Always use signature verification** - Either ngrok traffic policy OR application-level HMAC (production mode)
2. **Always use HTTPS** - ngrok provides this automatically; self-hosted requires SSL certificate
3. **Never commit secrets** - Use environment variables or secure secret management
4. **Restrict Slack bot permissions** - Only grant necessary OAuth scopes (`chat:write`, `channels:read`, etc.)
5. **Rotate secrets regularly** - Update `SLACK_SIGNING_SECRET` periodically (Slack recommends every few months)

**For Web Service Hosted (ngrok):**
6. **Use traffic policy verification** - Blocks invalid requests before they reach your app
7. **Monitor ngrok verification quota** - Free tier: 500/month, upgrade if needed
8. **Secure your ngrok config** - Don't commit `ngrok-slack-policy.yml` with secrets

**For Self-Hosted:**
9. **Enable production mode** - Set `SECURITY_MODE=production` for HMAC verification
10. **Monitor webhook logs** - Watch for invalid signatures, rate limit hits
11. **Adjust rate limits as needed** - Tune `RATE_LIMIT_MAX_REQUESTS` based on usage
12. **Use reverse proxy** - nginx or similar for HTTPS termination and additional security

**Why NOT IP allowlisting:** Slack uses dynamic AWS IPs that change frequently; use signature verification instead

#### Troubleshooting

**ngrok: "Invalid signature" errors:**
- Verify signing secret in `ngrok-slack-policy.yml` matches your Slack app
- Check Slack app: Basic Information → Signing Secret
- Ensure ngrok is started with `--traffic-policy-file` flag
- Test without policy first to isolate issue

**Self-hosted: "Invalid signature" errors:**
- Verify `SLACK_SIGNING_SECRET` environment variable matches your Slack app
- Check Slack app configuration: Basic Information → Signing Secret
- Ensure you're using the signing secret, NOT the client secret
- Verify `SECURITY_MODE=production` is set

**"Rate limit exceeded" errors (self-hosted only):**
- Default: 60 requests per 60 seconds per IP address
- This is normal if you're clicking approve/reject rapidly during testing
- To adjust limits, set environment variables:
  - `RATE_LIMIT_MAX_REQUESTS=120` (increase max requests)
  - `RATE_LIMIT_WINDOW_SECONDS=60` (time window in seconds)
- Rate limiting only applies in production mode

**Webhook not receiving requests:**
- Test ngrok URL: `curl https://your-ngrok-url.ngrok.io/health`
- Check Slack app configuration: Request URL must be `https://your-ngrok-url.ngrok.io/slack/interactive`
- Verify bot is installed to workspace
- Check webhook server logs for errors

**"Invalid approval_id format" warnings:**
- The webhook automatically blocks suspicious approval IDs (prevents path traversal)
- This is a security feature - if you see this, someone may be attempting an attack
- Valid approval IDs contain only: letters, numbers, hyphens, underscores

### Multiple Methods Working Together

**Approval methods work intelligently based on configuration:**

**When Slack is NOT enabled:**
1. **Native OS dialog** appears (macOS/Windows) - if `USE_NATIVE_DIALOG=true`
2. **File-based instructions** printed to logs (always enabled)
3. **Any method can approve** - whichever responds first wins!

**When Slack IS enabled:**
1. **Slack notification** sent to configured channel/DM
2. **File-based instructions** printed to logs (always enabled as CLI backup)
3. **Native OS dialog is automatically disabled** (prevents duplicate requests)
4. **Any method can approve** - Slack response or file-based approval

**Configuration:**
```bash
USE_LOCAL_APPROVAL=true       # Default: true - enables file-based logging
USE_NATIVE_DIALOG=true        # Default: true (macOS/Windows only, auto-disabled if Slack enabled)
ENABLE_SLACK=true             # Default: true (requires SLACK_BOT_TOKEN)
APPROVAL_TIMEOUT_SECONDS=300  # Default: 300 (5 minutes)
```

**Summary of Approval Methods:**

| Method | Platform | Requires Config | Notes |
|--------|----------|----------------|-------|
| **Native OS Dialog** | macOS/Windows | No | Auto-disabled when Slack enabled |
| **File-Based (CLI)** | All | No | Always enabled, prints to logs |
| **Slack** | All | Yes (token) | Disables native dialogs when enabled |

## Configuration Reference

### Debug Logging

Debug logging is available to help troubleshoot issues with tool detection, upstream server communication, and middleware interception. By default, debug logging is **disabled** to keep logs clean.

**Enable debug logging:**

Set the `DEBUG` environment variable to `true` (or `1`, `yes`, `on`):

```bash
# In your .env file
DEBUG=true

# Or in Claude Desktop config
"env": {
  "DEBUG": "true",
  ...
}
```

**What gets logged when DEBUG is enabled:**

- **Tool Detection**: Which detection strategies matched (allowlist, blocklist, convention, metadata, read-only)
- **Middleware**: Tool interception and mutating status
- **Upstream Communication**: Arguments sent to upstream tools and response structures
- **Schema Information**: Tool parameter schemas and required/optional fields

**Example debug output:**

```
[DEBUG] Middleware intercepting tool call: 'create_repository'
[DEBUG] Tool 'create_repository' detected as mutating via convention (prefix/suffix)
[DEBUG] Tool 'create_repository' is_mutating=True
[DEBUG] Calling upstream tool 'create_repository' with arguments: {'name': 'test', ...}
[DEBUG] Upstream tool 'create_repository' response structure: {...}
```

**Note:** Debug logs are written to `stderr` and will appear in Claude Desktop's logs. They do not affect normal operation when disabled.

### Environment Variables

See [`.env.example`](.env.example) for complete documentation. Key variables:

**Approval Settings:**
```bash
APPROVAL_TIMEOUT_SECONDS=300    # Timeout in seconds
USE_LOCAL_APPROVAL=true         # Enable local approval (file-based CLI logging)
USE_NATIVE_DIALOG=true          # Use native OS dialogs (auto-disabled if Slack enabled)
ENABLE_SLACK=true               # Enable Slack (requires token, disables native dialogs)
```

**Slack Configuration:**
```bash
SLACK_BOT_TOKEN=xoxb-...        # Bot token (required for Slack)
SLACK_CHANNEL=#approvals        # Channel name or ID
SLACK_USER_ID=U1234567890       # For DMs instead of channel
```

### Detection Settings

```bash
# Explicit allowlist (additive - marks these as mutating, but doesn't disable other detection)
DETECTION_ALLOWLIST=write_file,edit_file,create_directory,move_file

# Explicit blocklist (override - marks these as non-mutating even if convention/metadata detects them)
DETECTION_BLOCKLIST=read_file,list_directory,get_info

# Enable detection strategies (work for ALL tools, not just allowlist)
DETECTION_ENABLE_CONVENTION=true   # Detect by naming (write_, delete_, remove_, send_, etc.)
DETECTION_ENABLE_METADATA=true     # Detect by tool description keywords
```

**Detection Strategies (in priority order):**
1. **Blocklist**: Explicitly listed tools never require approval (highest priority override)
2. **Read-Only Detection**: Automatically detects read-only operations (no approval needed):
   - **Prefixes**: `get_`, `read_`, `list_`, `search_`, `find_`, `query_`, `fetch_`, `retrieve_`, `show_`, `view_`, `describe_`, `info_`, `check_`, `verify_`, etc.
   - **Suffixes**: `_get`, `_read`, `_list`, `_search`, `_find`, `_query`, `_fetch`, `_show`, `_view`, `_info`, etc.
   - **Keywords**: "read", "get", "list", "search", "find", "query", "fetch", "retrieve", "show", "view", "describe", "info", "status", "check", "verify", "read-only", etc.
3. **Allowlist**: Explicitly listed tools always require approval (high priority)
4. **Convention-Based (Mutating)**: Automatically detects tools with mutating prefixes/suffixes:
   - **File/resource operations**: `write_`, `delete_`, `remove_`, `create_`, `update_`, `edit_`, `modify_`, `move_`, `copy_`, etc.
   - **Communication operations**: `send_`, `email_`, `message_`, `tweet_`, `post_`, `share_`, `publish_`, `notify_`, `broadcast_`, `dm_`, `sms_`, etc.
   - **Payment/transaction operations**: `charge_`, `payment_`, `transaction_`, `purchase_`, `refund_`, etc.
   - **HTTP/API operations**: `put_`, `patch_`, etc.
   - **Suffixes**: `_delete`, `_remove`, `_write`, `_create`, `_send`, `_email`, `_tweet`, `_charge`, etc.
5. **Metadata-Based (Mutating)**: Analyzes tool descriptions for keywords like:
   - **File operations**: "delete", "remove", "create", "write", "modify", "update", etc.
   - **Communication**: "send", "email", "message", "tweet", "post", "share", "publish", "notify", "broadcast", "dm", "sms", "social media", etc.
   - **Payments**: "charge", "payment", "transaction", "purchase", "refund", "bill", "invoice", etc.

**Important:** The allowlist is **additive**, not exclusive. Convention and metadata detection work for **all tools**, not just those in the allowlist. This means:
- **File operations** like `delete_file`, `remove_item`, `write_file` are automatically detected
- **Communication operations** like `send_email`, `post_tweet`, `share_content`, `notify_user` are automatically detected
- **Payment operations** like `charge_card`, `process_payment`, `make_purchase` are automatically detected
- Tools with descriptions containing "delete", "send email", "post to social media", "charge payment", etc. are automatically detected
- You don't need to enumerate every possible mutating tool
- The allowlist is just for explicit overrides or tools that don't match conventions

**Examples of automatically detected operations:**

**Read-Only (No Approval Required):**
- `search_repositories` → Detected as read-only via `search_` prefix
- `get_file` → Detected as read-only via `get_` prefix
- `list_issues` → Detected as read-only via `list_` prefix
- `find_user` → Detected as read-only via `find_` prefix
- `query_database` → Detected as read-only via `query_` prefix
- Any tool with description "searches for repositories" → Detected as read-only via "search" keyword
- Any tool with description "gets information about" → Detected as read-only via "get" keyword

**Mutating (Requires Approval):**
- `send_email` → Detected via `send_` prefix
- `post_tweet` → Detected via `post_` prefix  
- `email_user` → Detected via `email_` prefix
- `charge_payment` → Detected via `charge_` prefix
- `notify_team` → Detected via `notify_` prefix
- Any tool with description "sends an email message" → Detected via "send" and "email" keywords
- Any tool with description "posts content to social media" → Detected via "post" and "social media" keywords

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

## Example: GitHub MCP Server

This example demonstrates using Cite-Before-Act MCP with the [GitHub MCP Server](https://github.com/github/github-mcp-server) to require approval for mutating GitHub operations.

### Quick Setup

1. **Install GitHub MCP Server**: Download from [GitHub Releases](https://github.com/github/github-mcp-server/releases) and add to PATH

2. **Create GitHub Personal Access Token**: Get a token at https://github.com/settings/tokens with required scopes

3. **Configure Claude Desktop**: Use the example configuration:

```json
{
  "mcpServers": {
    "cite-before-act-github": {
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "server.main", "--transport", "stdio"],
      "env": {
        "UPSTREAM_COMMAND": "github-mcp-server",
        "UPSTREAM_ARGS": "stdio",
        "UPSTREAM_TRANSPORT": "stdio",
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_your_token_here",
        "DETECTION_ENABLE_CONVENTION": "true",
        "DETECTION_ENABLE_METADATA": "true",
        "USE_LOCAL_APPROVAL": "true",
        "USE_NATIVE_DIALOG": "true"
      }
    }
  }
}
```

### What Gets Detected

The system automatically detects and requires approval for:
- **Repository operations**: `create_repository`, `delete_repository`, `update_repository`
- **File operations**: `create_file`, `update_file`, `delete_file`
- **Issue operations**: `create_issue`, `update_issue`, `add_issue_comment`, `close_issue`
- **Pull request operations**: `create_pull_request`, `merge_pull_request`, `close_pull_request`
- **Branch operations**: `create_branch`, `delete_branch`
- **Release operations**: `create_release`, `update_release`, `delete_release`
- **Social operations**: `star_repository`, `unstar_repository`
- And many more mutating operations...

**Read-only operations** (automatically allowed):
- `get_file`, `list_files`, `get_issue`, `list_issues`, `search_code`, etc.

### Example Workflow

1. User: "Create a new issue in my repo about fixing the login bug"
2. Cite-Before-Act intercepts `create_issue` tool call
3. Detection engine identifies it as mutating (via `create_` prefix)
4. Explain engine generates preview: "Create issue in owner/repo: Fix login bug"
5. Approval dialog appears
6. User approves
7. Issue is created

### Full Documentation

See [`examples/github_mcp_example.md`](examples/github_mcp_example.md) for complete setup instructions, Docker configuration, troubleshooting, and advanced options.

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
