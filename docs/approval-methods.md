# Approval Methods

Cite-Before-Act supports multiple approval methods that can work together intelligently.

## Local Approval (Default)

**Works out of the box - no configuration needed!**

### Native OS Dialogs

- **macOS**: Uses AppleScript (`osascript`) - no special permissions needed
- **Windows**: Uses PowerShell MessageBox
- **Linux**: File-based only (no native dialog available)
- **Note**: Native dialogs are automatically disabled when Slack is enabled

### File-Based Approval (CLI Logging)

- Instructions always printed to Claude Desktop logs (stderr)
- Works on all platforms
- Always enabled, even when Slack is configured
- Provides CLI backup for all approval methods
- **Approve**: `echo "approved" > /tmp/cite-before-act-approval-{id}.json`
- **Reject**: `echo "rejected" > /tmp/cite-before-act-approval-{id}.json`

## Slack Integration (Optional)

### Important Behavior

- **When Slack is enabled**: Native OS popup dialogs are automatically disabled
- **CLI logging still works**: File-based approval instructions are always printed to logs as a backup
- This prevents duplicate approval requests (Slack + popup) while maintaining CLI visibility

### Setup Steps

1. **Create Slack App** at https://api.slack.com/apps
2. **Add OAuth Scopes** (OAuth & Permissions):
   - `chat:write` - Send messages (required)
   - `channels:read` - List public channels
   - `groups:read` - List private channels (if using private channels)
   - `channels:join` - Join public channels
3. **Install to Workspace** and copy the Bot User OAuth Token
4. **Invite Bot to Channel**:
   - Private channels: `/invite @YourBotName` (required)
   - Public channels: Auto-joins with `channels:join` scope
5. **Configure Environment**:
   ```bash
   SLACK_BOT_TOKEN=xoxb-your-token-here
   SLACK_CHANNEL=#approvals  # Public: #name, Private: name (no #)
   ENABLE_SLACK=true
   ```

### Interactive Buttons (Optional)

To enable Approve/Reject buttons in Slack, you need to run a webhook server. See the [Slack Webhook Setup](slack-setup.md) guide for detailed configuration.

**Quick Setup:**
1. Run webhook server: `python examples/slack_webhook_server.py`
2. Expose with ngrok: `ngrok http 3000`
3. Configure in Slack: Interactive Components → Request URL → `https://your-ngrok-url.ngrok.io/slack/interactive`

Without webhooks, you'll still receive Slack notifications but must approve via file-based method or Slack reactions.

## Webex Teams Integration (Optional)

### Setup Steps

1. **Create Webex Bot** at https://developer.webex.com/my-apps
2. **Add Bot to Space/Room** where you want approvals sent
3. **Create Webhook** for attachment actions (button clicks)
4. **Configure Environment**:
   ```bash
   WEBEX_BOT_TOKEN=your-bot-token
   WEBEX_ROOM_ID=your-room-id       # For space/room messages
   # OR
   WEBEX_PERSON_EMAIL=user@example.com  # For direct messages
   ENABLE_WEBEX=true
   ```

### Interactive Buttons

Webex uses **adaptive cards** with built-in Approve/Reject buttons. When users click buttons:
1. Webex sends webhook POST to your server (`/webex/interactive`)
2. Webhook server processes the approval response
3. Response written to `/tmp/cite-before-act-webex-approval-{id}.json`
4. MCP server reads file and proceeds

**Setup webhook server:**
```bash
python examples/unified_webhook_server.py
```

**Configure webhook in Webex:**
- Create webhook for `attachmentActions` resource
- Target URL: `https://your-url/webex/interactive`

For complete setup instructions, see the [Webex Setup Guide](WEBEX_SETUP.md).

## Microsoft Teams Integration (Optional)

### Important: Account Requirements

**Requires a work or school Microsoft Teams account.** Personal Microsoft accounts are NOT supported.

### Setup Steps

1. **Create Azure App Registration** in Microsoft Entra ID
2. **Create Azure Bot Service** linked to your app
3. **Add Bot to Teams** via app manifest upload
4. **Start Webhook Server** to receive button clicks
5. **Configure Environment**:
   ```bash
   TEAMS_APP_ID=your-app-id
   TEAMS_APP_PASSWORD=your-app-password
   TEAMS_TENANT_ID=your-tenant-id  # Recommended (required for single-tenant)
   ENABLE_TEAMS=true
   ```

### Interactive Buttons

Teams uses **adaptive cards** via the Bot Framework. When users click buttons:
1. Teams sends invoke activity to your bot endpoint (`/api/messages`)
2. Webhook server processes the approval response
3. Response written to `/tmp/cite-before-act-teams-approval-{id}.json`
4. MCP server reads file and proceeds

**Setup webhook server:**
```bash
python examples/unified_webhook_server.py
```

**Configure in Azure:**
- Set messaging endpoint: `https://your-url/api/messages`

For complete setup instructions, see the [Teams Setup Guide](TEAMS_SETUP.md).

## Multiple Methods Working Together

Approval methods work intelligently based on configuration:

### When No Platforms Enabled (Local Only)

1. **Native OS dialog** appears (macOS/Windows) - if `USE_GUI_APPROVAL=true`
2. **File-based instructions** printed to logs (always enabled)
3. **Any method can approve** - whichever responds first wins!

### When Platforms ARE Enabled (Slack, Webex, Teams)

1. **Platform notifications** sent to all enabled platforms concurrently:
   - **Slack**: Message to configured channel/DM
   - **Webex**: Adaptive card to configured room/space
   - **Teams**: Adaptive card to configured channel/chat
2. **File-based instructions** printed to logs (always enabled as CLI backup)
3. **Native OS dialog is automatically disabled** (prevents duplicate requests)
4. **Any method can approve** - First response from any platform wins!

### Running Multiple Platforms Concurrently

You can enable **any combination** of platforms:

```bash
# Enable all platforms
ENABLE_SLACK=true
ENABLE_WEBEX=true
ENABLE_TEAMS=true
```

**How it works:**
- Approval requests sent to **all enabled platforms simultaneously**
- **First response wins** - user can respond via any platform
- Other platforms' responses are ignored (but buttons still work)
- File-based approval always available as universal fallback

See [Multi-Platform Approvals Guide](MULTI_PLATFORM_APPROVALS.md) for details.

## Configuration

```bash
# Local approval settings
USE_LOCAL_APPROVAL=true       # Default: true - enables file-based logging
USE_GUI_APPROVAL=true        # Default: true (macOS/Windows only, auto-disabled if platforms enabled)

# Platform integrations
ENABLE_SLACK=true             # Default: true (requires SLACK_BOT_TOKEN)
ENABLE_WEBEX=true             # Default: false (requires WEBEX_BOT_TOKEN)
ENABLE_TEAMS=true             # Default: false (requires TEAMS_APP_ID and TEAMS_APP_PASSWORD)

# Timeout
APPROVAL_TIMEOUT_SECONDS=300  # Default: 300 (5 minutes)
```

## Summary of Approval Methods

| Method | Platform | Requires Config | Notes |
|--------|----------|----------------|-------|
| **Native OS Dialog** | macOS/Windows | No | Auto-disabled when platforms enabled |
| **Slack** | All | Yes (token + webhook) | Interactive buttons |
| **Webex Teams** | All | Yes (bot token + webhook) | Adaptive cards |
| **Microsoft Teams** | All | Yes (Azure App + webhook) | Adaptive cards, requires work/school account |
| **File-Based (CLI)** | All | No | Always enabled, prints to logs |

## Next Steps

- [Slack Setup](slack-setup.md) - Configure Slack integration with interactive buttons
- [Webex Setup](WEBEX_SETUP.md) - Configure Webex Teams bot and adaptive cards
- [Teams Setup](TEAMS_SETUP.md) - Configure Teams bot with Azure
- [Multi-Platform Approvals](MULTI_PLATFORM_APPROVALS.md) - Using multiple platforms together
- [Configuration Reference](configuration.md) - Detailed configuration options
