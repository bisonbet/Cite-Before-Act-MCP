# Installation

This guide covers the different ways to install Cite-Before-Act MCP.

## Prerequisites

- Python 3.10 or higher
- Node.js 18+ and npm (for the filesystem MCP server)
- (Optional) Slack workspace with a bot token
- (Optional) ngrok account for webhook hosting

## Option 1: Automated Setup (Recommended)

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
- ✅ Generate descriptive server names (e.g., `github-cite`, `filesystem-cite`, `custom-server-cite`)

**Server Naming:** Server names follow the pattern `{upstream-server-name}-cite` to make it clear which upstream MCP server is being wrapped. For example:
- `github-cite` - Wraps the GitHub MCP server
- `filesystem-cite` - Wraps the filesystem MCP server
- `custom-server-cite` - Wraps a custom MCP server

This allows you to have multiple MCP servers wrapped by Cite-Before-Act MCP, each with its own configuration in Claude Desktop.

## Option 2: Manual Setup

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

See [`.env.example`](../.env.example) for all available options.

**Perfect for:** Advanced users, custom configurations, understanding the internals

## Next Steps

After installation, proceed to:
- [Claude Desktop Setup](claude-desktop-setup.md) - Configure Claude Desktop to use Cite-Before-Act
- [Installing Upstream Servers](upstream-servers.md) - Install MCP servers to wrap (GitHub, filesystem, etc.)
- [Configuration](configuration.md) - Learn about configuration options
