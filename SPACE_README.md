---
title: "Cite-Before-Act MCP"
emoji: "🛡️ "
colorFrom: "blue"
colorTo: "green"
sdk: "static"
python_version: "3.12"
license: "agpl-3.0"
short_description: "Human-in-the-loop safety middleware for MCP servers"
tags:
  - building-mcp-track-enterprise
  - building-mcp-track-customer
  - mcp
  - model-context-protocol
  - safety
  - human-in-the-loop
  - middleware
  - approval-workflow
  - fastmcp
---

# Cite-Before-Act MCP

An MCP middleware server that requires explicit approval for state-mutating tool calls. For any tool that mutates state (send email, charge card, delete file), it forces a "citation-first" dry-run with an LLM-readable preview; only on explicit approval does it execute.

## Overview

Cite-Before-Act MCP implements the "human-in-the-loop" safety pattern for MCP servers. It acts as a proxy that:

1. **Intercepts** all tool calls before execution
2. **Detects** mutating operations using multiple strategies
3. **Generates** human-readable previews of what would happen
4. **Requests** approval via concurrent methods (native dialogs, Slack buttons, file-based) - first response wins
5. **Executes** only after explicit approval

This provides a standardized "dry-run → approval → execute" workflow that other MCP servers can leverage.

## Features

- **Multi-Strategy Detection**: Identifies mutating tools via allowlist/blocklist, naming conventions, and metadata analysis
- **Natural Language Previews**: Generates human-readable descriptions of tool actions
- **Multi-Platform Approvals**: Support for Slack, Webex Teams, Microsoft Teams, native OS dialogs, and file-based CLI
- **Concurrent Approval Methods**: All enabled platforms run in parallel - respond via any method
- **First Response Wins**: User can approve/reject via any enabled platform - the first response is accepted
- **Smart Method Coordination**: Automatically disables native popups when platforms are enabled (prevents duplicates)
- **Works Out of the Box**: Local approval requires no configuration
- **FastMCP Based**: Built on FastMCP for easy integration and proxy capabilities
- **Configurable**: Flexible configuration via environment variables
- **Protocol-Agnostic**: Can wrap any MCP server regardless of implementation language

## Quick Start

```bash
git clone https://github.com/bisonbet/Cite-Before-Act-MCP.git
cd Cite-Before-Act-MCP
python3 setup_wizard.py
```

The setup wizard will guide you through:
- Creating a Python virtual environment
- Installing dependencies
- Configuring approval methods (Slack, Webex, Teams - all optional)
- Setting up webhooks (optional)
- Generating Claude Desktop configuration
- Creating startup scripts

## Documentation

Full documentation is available in the [GitHub repository](https://github.com/bisonbet/Cite-Before-Act-MCP):

- [Installation Guide](https://github.com/bisonbet/Cite-Before-Act-MCP/blob/main/docs/installation.md)
- [Configuration Reference](https://github.com/bisonbet/Cite-Before-Act-MCP/blob/main/docs/configuration.md)
- [Detection System](https://github.com/bisonbet/Cite-Before-Act-MCP/blob/main/docs/detection.md)
- [Approval Methods](https://github.com/bisonbet/Cite-Before-Act-MCP/blob/main/docs/approval-methods.md)
- [Architecture Overview](https://github.com/bisonbet/Cite-Before-Act-MCP/blob/main/docs/architecture.md)
- [Development Guide](https://github.com/bisonbet/Cite-Before-Act-MCP/blob/main/docs/development.md)

## Platform Setup Guides

- [Slack Setup](https://github.com/bisonbet/Cite-Before-Act-MCP/blob/main/docs/slack-setup.md)
- [Webex Teams Setup](https://github.com/bisonbet/Cite-Before-Act-MCP/blob/main/docs/WEBEX_SETUP.md)
- [Microsoft Teams Setup](https://github.com/bisonbet/Cite-Before-Act-MCP/blob/main/docs/TEAMS_SETUP.md)
- [Multi-Platform Approvals](https://github.com/bisonbet/Cite-Before-Act-MCP/blob/main/docs/MULTI_PLATFORM_APPROVALS.md)

## How It Works

```
Client → Cite-Before-Act Proxy → Middleware → Detection → Explain → Approval → Upstream Server
                                    ↓
                              (if mutating)
                                    ↓
                          Concurrent Approval Methods
                          (run in parallel, first response wins)
                                    ↓
                    ┌───────────────┼───────────────┬───────────────┐
                    │               │               │               │
              Native Dialog    Slack Button   Webex Card    Teams Card
              (macOS/Win)   (interactive msg) (adaptive)   (adaptive)
                    │               │               │               │
                    └───────────────┼───────────────┴───────────────┘
                                    ↓
                        User responds via any method
                                    ↓
                              Execute or Reject
```

## Example Workflow

1. User in Claude Desktop: "Create a file called test.txt with content 'Hello, World!'"
2. Cite-Before-Act intercepts the `write_file` tool call
3. Detection engine identifies it as mutating (via `write_` prefix)
4. Explain engine generates preview: "Write file: /path/test.txt (13 bytes)"
5. Approval requests sent concurrently via all enabled methods
6. User responds via **any method** (first response wins)
7. File is created (if approved) or rejected with error message
8. Result returned to Claude Desktop

**Read-only operations** (like `read_file`, `list_directory`) execute immediately without approval.

## Configuration Example

Wrap any MCP server with minimal configuration:

```json
{
  "mcpServers": {
    "github-cite": {
      "command": "python",
      "args": ["-m", "server.main", "--transport", "stdio"],
      "env": {
        "UPSTREAM_COMMAND": "docker",
        "UPSTREAM_ARGS": "run,-i,--rm,ghcr.io/github/github-mcp-server",
        "UPSTREAM_TRANSPORT": "stdio",
        "ENABLE_SLACK": "true",
        "SLACK_CHANNEL": "#approvals"
      }
    }
  }
}
```

## Supported Approval Methods

All enabled methods run **concurrently** (in parallel), and the **first response wins**:

| Method | Platform | Requires Config | When Active | Notes |
|--------|----------|----------------|-------------|-------|
| **Native OS Dialog** | macOS/Windows | No | When `USE_GUI_APPROVAL=true` and no platforms enabled | Interactive popup |
| **Slack** | All | Yes (token + webhook) | When `ENABLE_SLACK=true` | Interactive buttons |
| **Webex Teams** | All | Yes (bot token + webhook) | When `ENABLE_WEBEX=true` | Adaptive cards |
| **Microsoft Teams** | All | Yes (Azure App + webhook) | When `ENABLE_TEAMS=true` | Bot Framework |
| **File-Based (CLI)** | All | No | Always active | Instructions printed to logs |

## License

AGPL-3.0 - See [LICENSE](https://github.com/bisonbet/Cite-Before-Act-MCP/blob/main/LICENSE) file for details.

## Contributing

Contributions welcome! Please open an issue or pull request on [GitHub](https://github.com/bisonbet/Cite-Before-Act-MCP).

## Acknowledgments

- Built with [FastMCP](https://github.com/jlowin/fastmcp)
- Tested with [Official MCP Filesystem Server](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem)
- GitHub MCP Server support via [GitHub MCP Server](https://github.com/github/github-mcp-server)
