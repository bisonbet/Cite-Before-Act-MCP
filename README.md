# Cite-Before-Act MCP

An MCP middleware server that requires explicit approval for state-mutating tool calls. For any tool that mutates state (send email, charge card, delete file), it forces a "citation-first" dry-run with an LLM-readable preview; only on explicit approval does it execute.

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

For manual installation and configuration options, see the [Installation Guide](docs/installation.md).

## Documentation

### Getting Started
- **[Installation](docs/installation.md)** - Automated and manual installation methods
- **[Claude Desktop Setup](docs/claude-desktop-setup.md)** - Configure Claude Desktop to use Cite-Before-Act
- **[Installing Upstream Servers](docs/upstream-servers.md)** - Install MCP servers to wrap (GitHub, filesystem, etc.)
- **[Testing the Setup](docs/testing.md)** - Verify everything works correctly

### Configuration
- **[Configuration Reference](docs/configuration.md)** - Complete configuration guide and environment variables
- **[Detection System](docs/detection.md)** - How the detection engine identifies mutating operations
- **[Approval Methods](docs/approval-methods.md)** - Local, Slack, and file-based approval

### Advanced Topics
- **[Slack Webhook Setup](docs/slack-setup.md)** - Configure Slack integration and interactive buttons
- **[Advanced Usage](docs/advanced-usage.md)** - Use as a library, standalone server, custom integrations
- **[Architecture](docs/architecture.md)** - System architecture and project structure
- **[Development](docs/development.md)** - Contributing and development setup

### Examples
- **[GitHub MCP Server Example](docs/examples/github-example.md)** - Complete example with GitHub MCP server

## How It Works

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

### Example Workflow

1. User in Claude Desktop: "Create a file called test.txt with content 'Hello, World!'"
2. Cite-Before-Act intercepts the `write_file` tool call
3. Detection engine identifies it as mutating (via `write_` prefix)
4. Explain engine generates preview: "Write file: /path/test.txt (13 bytes)"
5. Approval request appears (native dialog, Slack, or file-based)
6. User approves
7. File is created
8. Result returned to Claude Desktop

**Read-only operations** (like `read_file`, `list_directory`) execute immediately without approval.

## Supported Approval Methods

| Method | Platform | Requires Config | Notes |
|--------|----------|----------------|-------|
| **Native OS Dialog** | macOS/Windows | No | Auto-disabled when Slack enabled |
| **File-Based (CLI)** | All | No | Always enabled, prints to logs |
| **Slack** | All | Yes (token) | Disables native dialogs when enabled |

See [Approval Methods](docs/approval-methods.md) for detailed configuration.

## Configuration

Cite-Before-Act uses a two-tier configuration system:

1. **`.env` file** - Global settings and secrets (Slack token, GitHub token, etc.)
2. **Claude Desktop config** - Per-server settings (upstream command, detection rules)

This allows you to:
- Share secrets across multiple wrapped MCP servers
- Configure each server differently
- Override global settings per-server if needed

See [Configuration Reference](docs/configuration.md) for details.

## Examples

### Wrapping the Filesystem Server

```json
{
  "mcpServers": {
    "filesystem-cite": {
      "command": "python",
      "args": ["-m", "server.main", "--transport", "stdio"],
      "env": {
        "UPSTREAM_COMMAND": "npx",
        "UPSTREAM_ARGS": "-y,@modelcontextprotocol/server-filesystem,/path/to/workspace",
        "UPSTREAM_TRANSPORT": "stdio"
      }
    }
  }
}
```

### Wrapping the GitHub MCP Server

```json
{
  "mcpServers": {
    "github-cite": {
      "command": "python",
      "args": ["-m", "server.main", "--transport", "stdio"],
      "env": {
        "UPSTREAM_COMMAND": "docker",
        "UPSTREAM_ARGS": "run,-i,--rm,ghcr.io/github/github-mcp-server",
        "UPSTREAM_TRANSPORT": "stdio"
      }
    }
  }
}
```

See [GitHub MCP Server Example](docs/examples/github-example.md) for complete setup.

## Development

```bash
# Clone and install
git clone https://github.com/bisonbet/Cite-Before-Act-MCP.git
cd Cite-Before-Act-MCP
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black .
ruff check .
```

See [Development Guide](docs/development.md) for details.

## License

AGPL-3.0 - See [LICENSE](LICENSE) file for details.

## Contributing

Contributions welcome! Please open an issue or pull request on GitHub.

See [Development Guide](docs/development.md) for contribution guidelines.

## Acknowledgments

- Built with [FastMCP](https://github.com/jlowin/fastmcp)
- Tested with [Official MCP Filesystem Server](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem)
- GitHub MCP Server support via [GitHub MCP Server](https://github.com/github/github-mcp-server)
