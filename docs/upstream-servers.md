# Installing Upstream MCP Servers

Cite-Before-Act is a **proxy/wrapper** that adds approval workflows to other MCP servers. You'll need to install at least one upstream MCP server to wrap.

## GitHub MCP Server (Local)

The GitHub MCP Server provides access to GitHub repositories, issues, pull requests, and more.

**Note:** The remote GitHub MCP server requires OAuth authentication which is complex. We recommend using the local version.

### Installation Options

#### 🐳 Docker (Recommended - Works on all platforms)

```bash
# Test the server (replace with your GitHub PAT)
docker run -i --rm \
  -e GITHUB_PERSONAL_ACCESS_TOKEN=ghp_your_token_here \
  ghcr.io/github/github-mcp-server

# For use with Cite-Before-Act, configure in .env:
UPSTREAM_COMMAND=docker
UPSTREAM_ARGS=run,-i,--rm,ghcr.io/github/github-mcp-server
UPSTREAM_TRANSPORT=stdio
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_your_token_here
```

**Pros:** No installation needed, works everywhere, always up-to-date
**Cons:** Requires Docker to be installed and running

#### 📦 Download Pre-built Binary

**macOS (Homebrew - Coming Soon):**
```bash
brew install github-mcp-server
```

**Windows (PowerShell):**
```powershell
# Download latest release
Invoke-WebRequest -Uri "https://github.com/github/github-mcp-server/releases/latest/download/github-mcp-server-windows-amd64.exe" -OutFile "github-mcp-server.exe"

# Move to a directory in PATH (or add current directory to PATH)
Move-Item github-mcp-server.exe C:\Windows\System32\
```

**Linux:**
```bash
# AMD64/x86_64
curl -L https://github.com/github/github-mcp-server/releases/latest/download/github-mcp-server-linux-amd64 -o github-mcp-server
chmod +x github-mcp-server
sudo mv github-mcp-server /usr/local/bin/

# ARM64
curl -L https://github.com/github/github-mcp-server/releases/latest/download/github-mcp-server-linux-arm64 -o github-mcp-server
chmod +x github-mcp-server
sudo mv github-mcp-server /usr/local/bin/
```

**After installation, configure in .env:**
```bash
UPSTREAM_COMMAND=github-mcp-server
UPSTREAM_ARGS=
UPSTREAM_TRANSPORT=stdio
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_your_token_here
```

**Pros:** Native performance, no Docker needed
**Cons:** Manual installation, need to update manually

#### 🔧 Build from Source (For Developers)

**Prerequisites:** Go 1.21 or higher

```bash
# Clone the repository
git clone https://github.com/github/github-mcp-server.git
cd github-mcp-server

# Build the binary
go build -o github-mcp-server ./cmd/github-mcp-server

# Move to PATH (optional)
sudo mv github-mcp-server /usr/local/bin/
```

**Configure in .env:**
```bash
UPSTREAM_COMMAND=github-mcp-server
UPSTREAM_ARGS=
UPSTREAM_TRANSPORT=stdio
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_your_token_here
```

**Pros:** Latest features, customizable
**Cons:** Requires Go toolchain, most complex setup

### Getting a GitHub Personal Access Token

1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scopes: `repo`, `workflow`, `write:packages`, `delete:packages`, `admin:org`
   (Or use minimal scopes for your specific use case)
4. Copy the token and save it to your `.env` file

## Filesystem Server

For file operations, no installation is needed - uses npx:

```bash
UPSTREAM_COMMAND=npx
UPSTREAM_ARGS=-y,@modelcontextprotocol/server-filesystem,/path/to/directory
UPSTREAM_TRANSPORT=stdio
```

## Other MCP Servers

For more MCP servers, see: https://github.com/modelcontextprotocol/servers

## Next Steps

After installing upstream servers:
- [Claude Desktop Setup](claude-desktop-setup.md) - Configure Claude Desktop
- [Configuration](configuration.md) - Configure upstream server settings
