# GitHub MCP Server Example

This example demonstrates how to use Cite-Before-Act MCP with the [GitHub MCP Server](https://github.com/github/github-mcp-server) to require approval for mutating GitHub operations like creating issues, pull requests, merging branches, etc.

---

## Table of Contents

1. [Quick Start (Recommended)](#quick-start-recommended)
2. [Prerequisites](#prerequisites)
3. [Option 1: Remote GitHub MCP Server (HTTP)](#option-1-remote-github-mcp-server-http)
4. [Option 2: Local GitHub MCP Server (stdio)](#option-2-local-github-mcp-server-stdio)
5. [What Gets Detected](#what-gets-detected)
6. [Example Workflow](#example-workflow)
7. [Advanced Configuration](#advanced-configuration)
8. [Testing](#testing)
9. [Troubleshooting](#troubleshooting)
10. [Resources](#resources)

---

## Quick Start (Recommended)

The easiest way to get started is using the **remote GitHub MCP Server** hosted by GitHub at `https://api.githubcopilot.com/mcp/`. This requires no local installation of the GitHub MCP server binary.

**Jump to:** [Option 1: Remote Server Setup](#option-1-remote-github-mcp-server-http)

---

## Prerequisites

### GitHub Personal Access Token

You'll need a GitHub Personal Access Token regardless of which option you choose.

1. Go to https://github.com/settings/tokens
2. Click **"Generate new token (classic)"**
3. Select scopes based on your needs:
   - **Full access:** `repo`, `workflow`, `write:packages`, `delete:packages`, `admin:org`, `admin:public_key`, `admin:repo_hook`, `admin:org_hook`, `gist`, `notifications`, `user`, `delete_repo`, `write:discussion`, `admin:enterprise`, `admin:gpg_key`
   - **Minimal (read + basic write):** `repo`, `workflow`
4. Copy the token and save it securely

---

## Option 1: Remote GitHub MCP Server (HTTP)

**Recommended for most users** - No local installation required.

### Advantages
- ✅ No need to download or install GitHub MCP server binary
- ✅ Always up-to-date with latest GitHub API changes
- ✅ Simpler setup
- ✅ Works on all platforms (macOS, Windows, Linux)

### Setup

#### Step 1: Configure Claude Desktop

Add the following to your Claude Desktop configuration file:

**Location:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

**Configuration (using secure token prompting):**

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
        "DETECTION_BLOCKLIST": "read_file,get_file,list_files,search_code,get_issue,list_issues,get_pull_request,list_pull_requests,search_repositories,get_repository,list_repositories,get_user,list_users,search_users",
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

**Alternative (token directly in config):**

If you prefer to store the token directly in the config:

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
        "DETECTION_BLOCKLIST": "read_file,get_file,list_files,search_code,get_issue,list_issues,get_pull_request,list_pull_requests,search_repositories,get_repository,list_repositories,get_user,list_users,search_users",
        "DETECTION_ENABLE_CONVENTION": "true",
        "DETECTION_ENABLE_METADATA": "true",
        "USE_LOCAL_APPROVAL": "true",
        "USE_GUI_APPROVAL": "true"
      }
    }
  }
}
```

**Configuration Notes:**
- Replace `/path/to/venv/bin/python` with your actual Python path (from Cite-Before-Act installation)
- Replace `ghp_your_token_here` with your GitHub Personal Access Token (if using direct token method)
- The `DETECTION_BLOCKLIST` ensures common read operations don't require approval

See the complete example: [`claude_desktop_config.github.remote.example.json`](../../claude_desktop_config.github.remote.example.json)

#### Step 2: Restart Claude Desktop

Restart Claude Desktop to load the new configuration.

#### Step 3: Test

Try a read operation: *"List my repositories"*

Try a mutating operation: *"Create a new issue in owner/repo titled 'Test Issue'"*

---

## Option 2: Local GitHub MCP Server (stdio)

**For users who want to run the GitHub MCP server locally.**

### Advantages
- ✅ Works offline (once server is installed)
- ✅ Full control over server version
- ✅ Can use Docker or binary

### Prerequisites

In addition to the GitHub token, you'll need to install the GitHub MCP Server:

#### Installation Option A: Using the Binary

1. Download the latest release from https://github.com/github/github-mcp-server/releases
2. Extract and place `github-mcp-server` in your PATH (e.g., `/usr/local/bin/`)
3. Make it executable: `chmod +x /path/to/github-mcp-server`

#### Installation Option B: Using Docker

No installation needed - Docker will pull the image automatically.

### Setup

#### Using the Binary

Add to your Claude Desktop configuration:

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
        "DETECTION_BLOCKLIST": "read_file,get_file,list_files,search_code,get_issue,list_issues,get_pull_request,list_pull_requests",
        "DETECTION_ENABLE_CONVENTION": "true",
        "DETECTION_ENABLE_METADATA": "true",
        "USE_LOCAL_APPROVAL": "true",
        "USE_GUI_APPROVAL": "true"
      }
    }
  }
}
```

**Configuration Notes:**
- Replace `/path/to/venv/bin/python` with your actual Python path
- Replace `ghp_your_token_here` with your GitHub Personal Access Token
- If `github-mcp-server` is not in your PATH, use the full path: `"/usr/local/bin/github-mcp-server"`

See the complete example: [`claude_desktop_config.github.example.json`](../../claude_desktop_config.github.example.json)

#### Using Docker

Add to your Claude Desktop configuration:

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

**Configuration Notes:**
- Replace `/path/to/venv/bin/python` with your actual Python path
- Replace `ghp_your_token_here` with your GitHub Personal Access Token
- Docker will automatically pull the image if not present

### Alternative: Using .env File

Instead of putting the token in Claude Desktop config, you can use a `.env` file in the Cite-Before-Act project root:

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
USE_GUI_APPROVAL=true
```

Then simplify your Claude Desktop config to just:

```json
{
  "mcpServers": {
    "cite-before-act-github": {
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "server.main", "--transport", "stdio"]
    }
  }
}
```

---

## What Gets Detected

The Cite-Before-Act MCP automatically detects and requires approval for mutating GitHub operations:

### Repository Operations
- ✅ `create_repository` - Create new repositories
- ✅ `delete_repository` - Delete repositories
- ✅ `update_repository` - Update repository settings
- ✅ `fork_repository` - Fork repositories

### File Operations
- ✅ `create_file` - Create new files
- ✅ `update_file` - Update existing files
- ✅ `delete_file` - Delete files
- ✅ `push_files` - Push multiple files

### Issue Operations
- ✅ `create_issue` - Create new issues
- ✅ `update_issue` - Update issue details
- ✅ `add_issue_comment` - Add comments to issues
- ✅ `close_issue` - Close issues
- ✅ `reopen_issue` - Reopen issues

### Pull Request Operations
- ✅ `create_pull_request` - Create new pull requests
- ✅ `update_pull_request` - Update PR details
- ✅ `merge_pull_request` - Merge pull requests
- ✅ `close_pull_request` - Close pull requests
- ✅ `add_pull_request_comment` - Add comments to PRs
- ✅ `request_reviewers` - Request PR reviews

### Branch Operations
- ✅ `create_branch` - Create new branches
- ✅ `delete_branch` - Delete branches
- ✅ `update_branch_protection` - Update branch protection rules

### Release Operations
- ✅ `create_release` - Create new releases
- ✅ `update_release` - Update releases
- ✅ `delete_release` - Delete releases

### Other Mutating Operations
- ✅ `star_repository` / `unstar_repository` - Star/unstar repositories
- ✅ `create_discussion` / `update_discussion` - Discussion operations
- ✅ `create_gist` / `update_gist` / `delete_gist` - Gist operations
- ✅ `add_collaborator` / `remove_collaborator` - Collaborator management
- ✅ `create_webhook` / `update_webhook` / `delete_webhook` - Webhook management
- And many more mutating operations...

### Read-Only Operations (Automatically Allowed)

These operations execute immediately **without requiring approval**:

- ❌ `get_file`, `read_file`, `list_files` - File reading
- ❌ `get_issue`, `list_issues` - Issue reading
- ❌ `get_pull_request`, `list_pull_requests` - PR reading
- ❌ `search_code`, `search_repositories` - Search operations
- ❌ `get_repository`, `list_repositories` - Repository reading
- ❌ `get_user`, `list_users` - User information
- And other read-only operations...

---

## Example Workflow

Here's a complete example of how the approval flow works:

### Scenario: Creating a GitHub Issue

1. **User asks Claude:** "Create a new issue in my-username/my-repo about fixing the login bug"

2. **Cite-Before-Act MCP intercepts** the `create_issue` tool call

3. **Detection engine identifies** it as mutating:
   - Matches `create_` prefix (convention-based detection)
   - Matches "create" keyword in description (metadata-based detection)

4. **Explain engine generates** a human-readable preview:
   ```
   Create issue in my-username/my-repo: Fix login bug
   ```

5. **Approval dialog appears** (one or more methods based on configuration):
   - **Native OS dialog:** Popup on macOS/Windows (if `USE_GUI_APPROVAL=true` and no platforms enabled)
   - **Slack:** Message with Approve/Reject buttons (if `ENABLE_SLACK=true`)
   - **Webex:** Adaptive card with buttons (if `ENABLE_WEBEX=true`)
   - **Teams:** Adaptive card with buttons (if `ENABLE_TEAMS=true`)
   - **File-based:** Instructions printed to logs (always available)

6. **User reviews and approves** via any available method

7. **Tool executes** and creates the issue on GitHub

8. **Result returned to Claude:** Issue URL and details

---

## Advanced Configuration

### Read-Only Mode

The GitHub MCP Server supports a `--read-only` flag that prevents all mutating operations at the server level:

```json
"UPSTREAM_ARGS": "stdio,--read-only"
```

This is useful for testing or when you want to ensure no operations can mutate state (even with approval).

### Lockdown Mode

GitHub MCP Server supports `--lockdown-mode` which limits content from public repositories:

```json
"UPSTREAM_ARGS": "stdio,--lockdown-mode"
```

### Dynamic Tool Discovery

GitHub MCP Server supports `--dynamic-toolsets` for dynamic tool discovery based on repository context:

```json
"UPSTREAM_ARGS": "stdio,--dynamic-toolsets"
```

### Combining Flags

You can combine multiple flags:

```json
"UPSTREAM_ARGS": "stdio,--lockdown-mode,--dynamic-toolsets"
```

### Custom Detection Rules

You can customize which operations require approval:

#### Allowlist (Force Approval)

```json
"DETECTION_ALLOWLIST": "star_repository,fork_repository"
```

Operations in the allowlist will **always** require approval, even if they might be detected as read-only.

#### Blocklist (Skip Approval)

```json
"DETECTION_BLOCKLIST": "read_file,get_file,list_files,search_code"
```

Operations in the blocklist will **never** require approval, even if they might be detected as mutating.

**Note:** Blocklist has **higher precedence** than allowlist for safety.

---

## Testing

After configuration, test your setup thoroughly:

### 1. Restart Claude Desktop

Restart Claude Desktop to load the new configuration.

### 2. Test Read Operations (Should Work Without Approval)

Try these commands in Claude Desktop:

- *"List my repositories"*
- *"Get details of issue #1 in owner/repo"*
- *"Search for code containing 'function' in my-username/my-repo"*
- *"Show me the README file from owner/repo"*

These should execute immediately without prompting for approval.

### 3. Test Mutating Operations (Should Require Approval)

Try these commands in Claude Desktop:

- *"Create a new issue in owner/repo titled 'Test Issue'"*
- *"Star the repository owner/repo"*
- *"Create a new file called test.txt in owner/repo with content 'Hello, World!'"*

These should trigger approval dialogs before executing.

### 4. Verify Approval Dialogs

Confirm that approval dialogs appear via your configured method(s):
- Native OS dialog appears (macOS/Windows, if enabled)
- Slack message with buttons (if configured)
- Webex adaptive card (if configured)
- Teams adaptive card (if configured)
- File-based instructions in Claude Desktop logs (always)

### 5. Test Approval and Rejection

- **Approve** an operation and verify it executes successfully
- **Reject** an operation and verify it returns an error to Claude

---

## Troubleshooting

### "Command not found: github-mcp-server" (Local Setup)

**Cause:** The binary is not in your PATH or doesn't exist.

**Solutions:**
1. Verify the binary exists: `which github-mcp-server`
2. Use the full path in `UPSTREAM_COMMAND`: `"/usr/local/bin/github-mcp-server"`
3. Verify the binary is executable: `chmod +x /path/to/github-mcp-server`
4. Download the binary from https://github.com/github/github-mcp-server/releases

### "Invalid token" or Authentication Errors

**Cause:** GitHub Personal Access Token is invalid, expired, or has insufficient permissions.

**Solutions:**
1. Verify your token is valid: https://github.com/settings/tokens
2. Check that the token has the required scopes (at minimum: `repo`, `workflow`)
3. Ensure the token hasn't expired
4. Generate a new token if needed
5. Verify the token is correctly set in configuration (check for extra spaces or quotes)

### Approval Dialogs Not Appearing

**Cause:** Approval method configuration issue.

**Solutions:**
1. Check `USE_LOCAL_APPROVAL=true` in configuration
2. Check `USE_GUI_APPROVAL=true` (or `false` if using Slack/Teams/Webex)
3. Verify Slack/Teams/Webex configuration if using those platforms
4. Check Claude Desktop logs for error messages
5. Verify file-based approval instructions appear in logs (always available)

### Operations Not Being Detected as Mutating

**Cause:** Detection engine not identifying operations correctly.

**Solutions:**
1. Ensure `DETECTION_ENABLE_CONVENTION=true`
2. Ensure `DETECTION_ENABLE_METADATA=true`
3. Check that the tool name matches mutating patterns (e.g., `create_`, `update_`, `delete_`)
4. Verify the tool is not in your `DETECTION_BLOCKLIST`
5. Enable debug logging: `DEBUG=true` to see detection decisions
6. Add the tool to `DETECTION_ALLOWLIST` to force approval

### Read Operations Requiring Approval

**Cause:** Tool incorrectly detected as mutating.

**Solutions:**
1. Add the tool to `DETECTION_BLOCKLIST` to skip approval
2. Check if the tool name uses mutating prefixes (e.g., `create_`, `update_`)
3. Enable debug logging: `DEBUG=true` to see why it's being detected as mutating
4. Verify `DETECTION_ENABLE_CONVENTION` and `DETECTION_ENABLE_METADATA` are properly set

### Remote Server Connection Failures (HTTP Transport)

**Cause:** Network issues or incorrect URL/authentication.

**Solutions:**
1. Verify the URL is correct: `https://api.githubcopilot.com/mcp/`
2. Check your internet connection
3. Verify the authentication header is correctly formatted
4. Check that `UPSTREAM_TRANSPORT` is set to `http`
5. Review Claude Desktop logs for connection error details

### Docker Issues (Local Setup with Docker)

**Cause:** Docker not running or incorrect configuration.

**Solutions:**
1. Verify Docker is running: `docker ps`
2. Test the Docker image manually: `docker run -i --rm ghcr.io/github/github-mcp-server --help`
3. Check that the token is correctly passed to Docker in `UPSTREAM_ARGS`
4. Verify Docker has permission to access the image registry

---

## Resources

### Official Documentation
- [GitHub MCP Server Repository](https://github.com/github/github-mcp-server)
- [GitHub MCP Server Documentation](https://github.com/github/github-mcp-server#readme)
- [GitHub Personal Access Tokens](https://github.com/settings/tokens)

### Cite-Before-Act Documentation
- [Configuration Reference](../configuration.md) - All environment variables and options
- [Detection System](../detection.md) - How detection works
- [Approval Methods](../approval-methods.md) - Overview of all approval methods
- [Installing Upstream Servers](../upstream-servers.md) - Detailed upstream server setup
- [Advanced Usage](../advanced-usage.md) - Using as a library, custom integrations

### MCP Resources
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [Official MCP Servers](https://github.com/modelcontextprotocol/servers)
- [FastMCP Framework](https://github.com/jlowin/fastmcp)

---

**Need help?** Open an issue on [GitHub](https://github.com/bisonbet/Cite-Before-Act-MCP/issues) or refer to the [troubleshooting guide](../testing.md).
