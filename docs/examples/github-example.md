# Example: GitHub MCP Server

This example demonstrates using Cite-Before-Act MCP with the [GitHub MCP Server](https://github.com/github/github-mcp-server) to require approval for mutating GitHub operations.

## Option 1: Remote GitHub MCP Server (HTTP Transport)

This is the recommended approach for using the official GitHub MCP Server hosted at `https://api.githubcopilot.com/mcp/`.

### Setup

1. **Create GitHub Personal Access Token**: Get a token at https://github.com/settings/tokens with required scopes

2. **Configure Claude Desktop**: Use the remote server configuration:

```json
{
  "mcpServers": {
    "cite-before-act-github-remote": {
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "server.main", "--transport", "stdio"],
      "env": {
        "UPSTREAM_URL": "https://api.githubcopilot.com/mcp/",
        "UPSTREAM_TRANSPORT": "http",
        "UPSTREAM_HEADER_Authorization": "Bearer ${input:github_mcp_pat}",
        "DETECTION_ENABLE_CONVENTION": "true",
        "DETECTION_ENABLE_METADATA": "true",
        "USE_LOCAL_APPROVAL": "true",
        "USE_GUI_APPROVAL": "true"
      }
    }
  },
  "inputs": [
    {
      "type": "promptString",
      "id": "github_mcp_pat",
      "description": "GitHub Personal Access Token",
      "password": true
    }
  ]
}
```

### Alternative (direct token in env)

```json
{
  "mcpServers": {
    "cite-before-act-github-remote": {
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "server.main", "--transport", "stdio"],
      "env": {
        "UPSTREAM_URL": "https://api.githubcopilot.com/mcp/",
        "UPSTREAM_TRANSPORT": "http",
        "UPSTREAM_AUTH_TOKEN": "ghp_your_token_here",
        "DETECTION_ENABLE_CONVENTION": "true",
        "DETECTION_ENABLE_METADATA": "true",
        "USE_LOCAL_APPROVAL": "true",
        "USE_GUI_APPROVAL": "true"
      }
    }
  }
}
```

See [`claude_desktop_config.github.remote.example.json`](../../claude_desktop_config.github.remote.example.json) for the complete example.

## Option 2: Local GitHub MCP Server (stdio Transport)

If you prefer to run the GitHub MCP Server locally:

### Setup

1. **Install GitHub MCP Server**: Download from [GitHub Releases](https://github.com/github/github-mcp-server/releases) and add to PATH

2. **Create GitHub Personal Access Token**: Get a token at https://github.com/settings/tokens with required scopes

3. **Configure Claude Desktop**: Use the local server configuration:

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
        "USE_GUI_APPROVAL": "true"
      }
    }
  }
}
```

## What Gets Detected

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

## Example Workflow

1. User: "Create a new issue in my repo about fixing the login bug"
2. Cite-Before-Act intercepts `create_issue` tool call
3. Detection engine identifies it as mutating (via `create_` prefix)
4. Explain engine generates preview: "Create issue in owner/repo: Fix login bug"
5. Approval dialog appears
6. User approves
7. Issue is created

## Getting a GitHub Personal Access Token

1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scopes: `repo`, `workflow`, `write:packages`, `delete:packages`, `admin:org`
   (Or use minimal scopes for your specific use case)
4. Copy the token and save it to your `.env` file or Claude Desktop config

## Related Documentation

- [Installing Upstream Servers](../upstream-servers.md) - Detailed GitHub MCP server installation
- [Detection System](../detection.md) - How detection works
- [Configuration](../configuration.md) - Configuration options
