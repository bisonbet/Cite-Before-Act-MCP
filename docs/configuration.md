# Configuration Reference

This guide covers all configuration options for Cite-Before-Act MCP.

## Configuration Architecture

Cite-Before-Act uses a **two-tier configuration system** that separates secrets, global settings, and per-server configuration:

### 1. `.env` File (Global Defaults and Secrets)

**Purpose:** Store secrets and global settings that apply to ALL wrapped MCP servers

**Contains:**
- 🔐 **Secrets**: `GITHUB_PERSONAL_ACCESS_TOKEN`, `SLACK_BOT_TOKEN`, etc.
- 🌍 **Global Settings**: `ENABLE_SLACK`, `USE_LOCAL_APPROVAL`, `APPROVAL_TIMEOUT_SECONDS`
- ⚙️ **Global Detection Defaults**: `DETECTION_ENABLE_CONVENTION`, `DETECTION_ENABLE_METADATA`

**Location:** Project root directory (same as `.env.example`)

**Example `.env` file:**
```bash
# =============================================================================
# Secrets (NEVER commit to git!)
# =============================================================================
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_your_token_here
SLACK_BOT_TOKEN=xoxb-your-token-here

# =============================================================================
# Global Settings (apply to ALL servers)
# =============================================================================
# Slack Configuration
ENABLE_SLACK=true
SLACK_CHANNEL=#approvals

# Approval Settings
APPROVAL_TIMEOUT_SECONDS=300
USE_LOCAL_APPROVAL=true
USE_GUI_APPROVAL=false  # Disabled when Slack is enabled

# Detection Defaults
DETECTION_ENABLE_CONVENTION=true
DETECTION_ENABLE_METADATA=true
```

### 2. Claude Desktop Config (Per-Server Configuration)

**Purpose:** Configure each individual upstream MCP server you're wrapping

**Contains:**
- 🎯 **Server-Specific Config**: `UPSTREAM_COMMAND`, `UPSTREAM_ARGS`, `UPSTREAM_TRANSPORT`, `UPSTREAM_URL`
- 🎛️ **Per-Server Detection Overrides**: `DETECTION_ALLOWLIST`, `DETECTION_BLOCKLIST`
- 🔄 **Optional Per-Server Overrides**: Can override global settings if needed

**Example Claude Desktop config with multiple servers:**
```json
{
  "mcpServers": {
    "filesystem-cite": {
      "command": "/path/to/.venv/bin/python",
      "args": ["-m", "server.main", "--transport", "stdio"],
      "env": {
        "UPSTREAM_COMMAND": "npx",
        "UPSTREAM_ARGS": "-y,@modelcontextprotocol/server-filesystem,/Users/yourname/workspace",
        "UPSTREAM_TRANSPORT": "stdio",
        "DETECTION_ALLOWLIST": "write_file,edit_file,create_directory",
        "DETECTION_BLOCKLIST": "read_file,list_directory"
      }
    },
    "github-cite": {
      "command": "/path/to/.venv/bin/python",
      "args": ["-m", "server.main", "--transport", "stdio"],
      "env": {
        "UPSTREAM_COMMAND": "docker",
        "UPSTREAM_ARGS": "run,-i,--rm,ghcr.io/github/github-mcp-server",
        "UPSTREAM_TRANSPORT": "stdio",
        "DETECTION_ALLOWLIST": "",
        "DETECTION_BLOCKLIST": "read_file,get_file,list_files,search_code"
      }
    }
  }
}
```

### Environment Variable Precedence

**Priority Order:**
1. **mcpServers.env** (highest) - Per-server overrides in Claude Desktop config
2. **.env file** (lower) - Global defaults and secrets

This allows you to:
- ✅ **Share secrets** across multiple wrapped servers (GitHub token works for all GitHub servers)
- ✅ **Use same Slack config** for all servers (one channel for all approvals)
- ✅ **Configure each server differently** (different upstream commands, detection rules)
- ✅ **Override global settings per-server** if needed (e.g., different timeout for specific server)

**Example with override:**
```bash
# .env (global default)
APPROVAL_TIMEOUT_SECONDS=300

# Claude Desktop config (override for this server only)
"critical-operations-cite": {
  "env": {
    "APPROVAL_TIMEOUT_SECONDS": "600",  # 10 minutes instead of 5
    "UPSTREAM_COMMAND": "...",
    ...
  }
}
```

### How It Works

- The `.env` file is loaded by `config/settings.py` using `python-dotenv`
- Uses **absolute path** to find `.env` in project root (works regardless of launch directory)
- `load_dotenv()` does NOT override existing environment variables
- Claude Desktop sets mcpServers.env vars first, then `.env` fills in the rest
- **Result:** Per-server config takes precedence, `.env` provides global defaults

### Benefits

- 🔒 **Security**: Secrets stay in `.env`, never in Claude Desktop config
- 🌐 **Cross-Platform**: Works on macOS, Windows, Linux (no OS-specific issues)
- 📦 **Multi-Server**: Share secrets and global settings across all wrapped servers
- 🎯 **Flexibility**: Per-server customization when needed
- 🔄 **Maintainable**: Update global settings in one place (`.env`)

## Environment Variables

See [`.env.example`](../.env.example) for complete documentation.

### Global Variables (in `.env` file)

These apply to ALL wrapped MCP servers:

**Secrets:**
```bash
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_...  # GitHub PAT (secret)
SLACK_BOT_TOKEN=xoxb-...              # Slack bot token (secret)
UPSTREAM_AUTH_TOKEN=...               # Generic auth token (secret)
```

**Approval Settings:**
```bash
APPROVAL_TIMEOUT_SECONDS=300    # Timeout in seconds
USE_LOCAL_APPROVAL=true         # Enable local approval (GUI/file-based)
USE_GUI_APPROVAL=true          # Use native OS dialogs (auto-disabled if Slack enabled)
ENABLE_SLACK=true               # Enable Slack (requires token, disables native dialogs)
```

**Slack Configuration:**
```bash
SLACK_CHANNEL=#approvals        # Channel name or ID
SLACK_USER_ID=U1234567890       # For DMs instead of channel
```

**Detection Defaults:**
```bash
DETECTION_ENABLE_CONVENTION=true   # Detect by naming (write_, delete_, etc.)
DETECTION_ENABLE_METADATA=true     # Detect by description keywords
```

### Per-Server Variables (in Claude Desktop `mcpServers.env`)

These are specific to each wrapped MCP server:

**Upstream Server Configuration:**
```bash
UPSTREAM_COMMAND=docker                           # Command to run upstream server
UPSTREAM_ARGS=run,-i,--rm,ghcr.io/github/...     # Arguments (comma-separated)
UPSTREAM_TRANSPORT=stdio                          # Transport: stdio, http, or sse
UPSTREAM_URL=http://localhost:3010                # URL (for http/sse transport)
```

**Detection Overrides (optional per-server):**
```bash
DETECTION_ALLOWLIST=write_file,edit_file          # Tools that always need approval
DETECTION_BLOCKLIST=read_file,list_directory      # Tools that never need approval
```

## Detection Settings

Detection settings work across two levels:

### Global Defaults (`.env` file)

```bash
# Enable detection strategies (work for ALL tools across all servers)
DETECTION_ENABLE_CONVENTION=true   # Detect by naming (write_, delete_, remove_, send_, etc.)
DETECTION_ENABLE_METADATA=true     # Detect by tool description keywords
```

### Per-Server Overrides (Claude Desktop `mcpServers.env`)

```bash
# Explicit allowlist (additive - marks these as mutating, but doesn't disable other detection)
DETECTION_ALLOWLIST=write_file,edit_file,create_directory,move_file

# Explicit blocklist (override - marks these as non-mutating even if convention/metadata detects them)
DETECTION_BLOCKLIST=read_file,list_directory,get_info
```

**Why split these?**
- Different upstream servers have different tool names (GitHub: `create_repository`, Filesystem: `write_file`)
- Each server needs its own allowlist/blocklist tailored to its tools
- Global detection strategies (convention, metadata) work universally across all servers

For detailed information about detection strategies, see [Detection Guide](detection.md).

## Upstream Server Configuration

### stdio transport (subprocess)

```bash
UPSTREAM_COMMAND=npx
UPSTREAM_ARGS=-y,@modelcontextprotocol/server-filesystem,/absolute/path
UPSTREAM_TRANSPORT=stdio
```

### HTTP transport (remote server)

```bash
UPSTREAM_URL=https://api.example.com/mcp/
UPSTREAM_TRANSPORT=http
UPSTREAM_HEADER_Authorization=Bearer your-token-here
```

### SSE transport (Server-Sent Events)

```bash
UPSTREAM_URL=https://api.example.com/mcp/
UPSTREAM_TRANSPORT=sse
UPSTREAM_HEADER_Authorization=Bearer your-token-here
```

**Note:** GitHub MCP server remote (`api.githubcopilot.com`) automatically uses SSE transport even if configured as `http`. You can use either `http` or `sse` - both work.

### Multiple headers (comma-separated)

```bash
UPSTREAM_URL=https://api.example.com/mcp/
UPSTREAM_TRANSPORT=http
UPSTREAM_HEADERS=Authorization:Bearer token, X-Custom-Header:value
```

### Individual header environment variables

```bash
UPSTREAM_URL=https://api.example.com/mcp/
UPSTREAM_TRANSPORT=http
UPSTREAM_HEADER_Authorization=Bearer your-token-here
UPSTREAM_HEADER_X-Custom-Header=custom-value
```

## Debug Logging

Debug logging is available to help troubleshoot issues with tool detection, upstream server communication, and middleware interception. By default, debug logging is **disabled** to keep logs clean.

### Enable debug logging

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

### What gets logged when DEBUG is enabled

- **Tool Detection**: Which detection strategies matched (allowlist, blocklist, convention, metadata, read-only)
- **Middleware**: Tool interception and mutating status
- **Upstream Communication**: Arguments sent to upstream tools and response structures
- **Schema Information**: Tool parameter schemas and required/optional fields

### Example debug output

```
[DEBUG] Middleware intercepting tool call: 'create_repository'
[DEBUG] Tool 'create_repository' detected as mutating via convention (prefix/suffix)
[DEBUG] Tool 'create_repository' is_mutating=True
[DEBUG] Calling upstream tool 'create_repository' with arguments: {'name': 'test', ...}
[DEBUG] Upstream tool 'create_repository' response structure: {...}
```

**Note:** Debug logs are written to `stderr` and will appear in Claude Desktop's logs. They do not affect normal operation when disabled.

## Setup

### Automatic (Recommended)

```bash
python3 setup_wizard.py
```
The wizard automatically creates both `.env` and Claude Desktop config with the correct split.

### Manual

1. **Copy the example file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` and add your secrets:**
   ```bash
   GITHUB_PERSONAL_ACCESS_TOKEN=ghp_your_token_here
   SLACK_BOT_TOKEN=xoxb-your-token-here
   SLACK_CHANNEL=#approvals
   ```

3. **Add server-specific config to Claude Desktop** (see examples above)
