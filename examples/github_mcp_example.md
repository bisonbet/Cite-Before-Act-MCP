# GitHub MCP Server Example

This example demonstrates how to use Cite-Before-Act MCP with the [GitHub MCP Server](https://github.com/github/github-mcp-server) to require approval for mutating GitHub operations like creating issues, pull requests, merging branches, etc.

## Prerequisites

1. **GitHub Personal Access Token**: Create a token with appropriate permissions at https://github.com/settings/tokens
   - Required scopes: `repo`, `workflow`, `write:packages`, `delete:packages`, `admin:org`, `admin:public_key`, `admin:repo_hook`, `admin:org_hook`, `gist`, `notifications`, `user`, `delete_repo`, `write:discussion`, `admin:enterprise`, `admin:gpg_key`
   - Or use the minimal scopes needed for your use case

2. **GitHub MCP Server Binary**: Download from [GitHub Releases](https://github.com/github/github-mcp-server/releases) or build from source
   - Place the binary in your PATH, or use the full path in configuration

## Installation

### Option 1: Using the Binary

1. Download the latest release from https://github.com/github/github-mcp-server/releases
2. Extract and place `github-mcp-server` in your PATH (or use full path in config)

### Option 2: Using Docker

If using Docker, you'll need to configure the upstream differently. See the [Docker section](#docker-setup) below.

## Configuration

### Claude Desktop Configuration

Copy [`claude_desktop_config.github.example.json`](../claude_desktop_config.github.example.json) and customize:

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

**Important Notes:**
- Replace `/path/to/venv/bin/python` with your actual Python path
- Replace `ghp_your_token_here` with your GitHub Personal Access Token
- If `github-mcp-server` is not in your PATH, use the full path: `"/usr/local/bin/github-mcp-server"` or `"/path/to/github-mcp-server"`

### Environment Variables (.env file)

Alternatively, you can use a `.env` file:

```bash
# GitHub MCP Server Configuration
UPSTREAM_COMMAND=github-mcp-server
UPSTREAM_ARGS=stdio
UPSTREAM_TRANSPORT=stdio
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_your_token_here

# Detection Settings
DETECTION_ENABLE_CONVENTION=true
DETECTION_ENABLE_METADATA=true
DETECTION_BLOCKLIST=read_file,get_file,list_files,search_code,get_issue,list_issues,get_pull_request,list_pull_requests

# Approval Settings
APPROVAL_TIMEOUT_SECONDS=300
USE_LOCAL_APPROVAL=true
USE_NATIVE_DIALOG=true
```

## What Gets Detected

The Cite-Before-Act MCP will automatically detect and require approval for mutating GitHub operations such as:

### Repository Operations
- `create_repository` - Create new repositories
- `delete_repository` - Delete repositories
- `update_repository` - Update repository settings

### File Operations
- `create_file` - Create new files
- `update_file` - Update existing files
- `delete_file` - Delete files

### Issue Operations
- `create_issue` - Create new issues
- `update_issue` - Update issue details
- `add_issue_comment` - Add comments to issues
- `close_issue` - Close issues
- `reopen_issue` - Reopen issues

### Pull Request Operations
- `create_pull_request` - Create new pull requests
- `update_pull_request` - Update PR details
- `merge_pull_request` - Merge pull requests
- `close_pull_request` - Close pull requests
- `add_pull_request_comment` - Add comments to PRs

### Branch Operations
- `create_branch` - Create new branches
- `delete_branch` - Delete branches

### Release Operations
- `create_release` - Create new releases
- `update_release` - Update releases
- `delete_release` - Delete releases

### Other Mutating Operations
- `star_repository` / `unstar_repository` - Star/unstar repositories
- `create_discussion` / `update_discussion` - Create/update discussions
- `create_gist` / `update_gist` / `delete_gist` - Gist operations
- And many more...

**Read-only operations** (automatically allowed through):
- `get_file`, `read_file`, `list_files`
- `get_issue`, `list_issues`
- `get_pull_request`, `list_pull_requests`
- `search_code`, `search_repositories`
- And other read operations

## Example Workflow

1. **User asks Claude**: "Create a new issue in my repo about fixing the login bug"

2. **Cite-Before-Act MCP intercepts** the `create_issue` tool call

3. **Detection engine identifies** it as mutating (via `create_` prefix)

4. **Explain engine generates** a preview: "Create issue in owner/repo: Fix login bug"

5. **Approval dialog appears** (native OS dialog or Slack notification)

6. **User reviews and approves**

7. **Tool executes** and creates the issue

## Docker Setup

If you prefer to use the GitHub MCP Server via Docker:

```json
{
  "mcpServers": {
    "cite-before-act-github": {
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "server.main", "--transport", "stdio"],
      "env": {
        "UPSTREAM_COMMAND": "docker",
        "UPSTREAM_ARGS": "run,-i,--rm,-e,GITHUB_PERSONAL_ACCESS_TOKEN=ghp_your_token_here,ghcr.io/github/github-mcp-server,stdio",
        "UPSTREAM_TRANSPORT": "stdio",
        "DETECTION_ENABLE_CONVENTION": "true",
        "DETECTION_ENABLE_METADATA": "true",
        "USE_LOCAL_APPROVAL": "true"
      }
    }
  }
}
```

## Read-Only Mode

The GitHub MCP Server supports a `--read-only` flag. If you want to use read-only mode while still having the proxy for future mutating operations:

```json
"UPSTREAM_ARGS": "stdio,--read-only"
```

## Advanced Configuration

### Lockdown Mode

GitHub MCP Server supports `--lockdown-mode` which limits content from public repositories. To use it:

```json
"UPSTREAM_ARGS": "stdio,--lockdown-mode"
```

### Dynamic Tool Discovery

GitHub MCP Server supports `--dynamic-toolsets` for dynamic tool discovery:

```json
"UPSTREAM_ARGS": "stdio,--dynamic-toolsets"
```

## Testing

After configuration, test the setup:

1. **Restart Claude Desktop** to load the new configuration

2. **Try a read operation** (should work without approval):
   - "List my repositories"
   - "Get details of issue #1 in owner/repo"

3. **Try a mutating operation** (should require approval):
   - "Create a new issue in owner/repo titled 'Test Issue'"
   - "Star the repository owner/repo"

4. **Verify approval dialogs** appear for mutating operations

## Troubleshooting

### "Command not found: github-mcp-server"

- Ensure the binary is in your PATH, or use the full path in `UPSTREAM_COMMAND`
- Verify the binary is executable: `chmod +x github-mcp-server`

### "Invalid token" or authentication errors

- Verify your GitHub Personal Access Token is valid
- Check that the token has the required scopes
- Ensure the token hasn't expired

### Approval dialogs not appearing

- Check `USE_LOCAL_APPROVAL=true` in configuration
- Check `USE_NATIVE_DIALOG=true` (or `false` if using Slack)
- Verify Slack configuration if using Slack approval

### Operations not being detected as mutating

- Ensure `DETECTION_ENABLE_CONVENTION=true`
- Ensure `DETECTION_ENABLE_METADATA=true`
- Check that the tool name matches mutating patterns (e.g., `create_`, `update_`, `delete_`)

## Resources

- [GitHub MCP Server Repository](https://github.com/github/github-mcp-server)
- [GitHub MCP Server Documentation](https://github.com/github/github-mcp-server#readme)
- [GitHub Personal Access Tokens](https://github.com/settings/tokens)

