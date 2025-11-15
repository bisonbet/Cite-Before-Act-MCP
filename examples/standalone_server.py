"""Example: Running the standalone proxy server.

This example shows how to configure and run the Cite-Before-Act MCP proxy server
to wrap the official MCP Filesystem Server.
"""

# Example .env file configuration:
"""
# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-token-here
SLACK_CHANNEL=#approvals
# SLACK_USER_ID=U1234567890  # Optional: for DMs instead of channel

# Detection Configuration
DETECTION_ALLOWLIST=write_file,edit_file,create_directory,move_file,delete_file
DETECTION_BLOCKLIST=read_text_file,read_media_file,list_directory,get_file_info
DETECTION_ENABLE_CONVENTION=true
DETECTION_ENABLE_METADATA=true

# Upstream Server Configuration (Official MCP Filesystem Server)
# Option 1: stdio transport (run as subprocess)
UPSTREAM_COMMAND=npx
UPSTREAM_ARGS=-y,@modelcontextprotocol/server-filesystem
UPSTREAM_TRANSPORT=stdio

# Option 2: HTTP transport (if server is running separately)
# UPSTREAM_URL=http://localhost:3010
# UPSTREAM_TRANSPORT=http

# Approval Settings
APPROVAL_TIMEOUT_SECONDS=300
ENABLE_SLACK=true
"""

# To run the server:
# 1. Create a .env file with the configuration above
# 2. Install dependencies: pip install -e .
# 3. Run: python -m server.main --transport stdio
#    Or: python -m server.main --transport http --host 0.0.0.0 --port 8000

if __name__ == "__main__":
    print("See README.md for instructions on running the standalone server.")
    print("\nExample command:")
    print("  python -m server.main --transport stdio")

