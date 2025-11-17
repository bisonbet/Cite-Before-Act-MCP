# Claude Desktop Setup

This guide walks you through configuring Claude Desktop to use Cite-Before-Act MCP.

## Step-by-Step Configuration

### 1. Create Test Directory

```bash
mkdir -p ~/mcp-test-workspace
cd ~/mcp-test-workspace && pwd  # Copy this absolute path
```

### 2. Locate Claude Desktop Config File

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

### 3. Add Configuration

**Quick Setup:** Copy the configuration from [`claude_desktop_config.example.json`](../claude_desktop_config.example.json) and paste into your `claude_desktop_config.json`, then edit as needed.

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
        "USE_GUI_APPROVAL": "true"
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

### 4. Update Paths

- Replace `/Users/yourname/mcp-test-workspace` with the absolute path from step 1
- If using a virtual environment, use the full path to Python (e.g., `/path/to/venv/bin/python`)

### 5. Restart Claude Desktop

- Completely quit Claude Desktop
- Reopen the application
- Verify the server is connected and tools are available

## Troubleshooting

### Server not appearing

- Verify JSON syntax is valid
- Check Python path is correct
- Ensure dependencies are installed
- Review Claude Desktop logs for errors

### Only seeing `explain` tool (no filesystem tools)

1. Verify Node.js is installed: `node --version`
2. Test upstream server: `npx -y @modelcontextprotocol/server-filesystem /path/to/test/directory`
3. Use absolute paths (not `~` or relative paths)
4. Ensure test directory exists

### Slack channel errors

- **Private channels**: Use `approvals` (no `#`), invite bot with `/invite @YourBotName`
- **Public channels**: Use `#approvals` (with `#`)
- Verify bot has required OAuth scopes (`chat:write`, `channels:read`)

## Next Steps

- [Testing the Setup](testing.md) - Verify everything works correctly
- [Approval Methods](approval-methods.md) - Learn about different approval methods
