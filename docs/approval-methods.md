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

## Multiple Methods Working Together

Approval methods work intelligently based on configuration:

### When Slack is NOT enabled

1. **Native OS dialog** appears (macOS/Windows) - if `USE_GUI_APPROVAL=true`
2. **File-based instructions** printed to logs (always enabled)
3. **Any method can approve** - whichever responds first wins!

### When Slack IS enabled

1. **Slack notification** sent to configured channel/DM
2. **File-based instructions** printed to logs (always enabled as CLI backup)
3. **Native OS dialog is automatically disabled** (prevents duplicate requests)
4. **Any method can approve** - Slack response or file-based approval

## Configuration

```bash
USE_LOCAL_APPROVAL=true       # Default: true - enables file-based logging
USE_GUI_APPROVAL=true        # Default: true (macOS/Windows only, auto-disabled if Slack enabled)
ENABLE_SLACK=true             # Default: true (requires SLACK_BOT_TOKEN)
APPROVAL_TIMEOUT_SECONDS=300  # Default: 300 (5 minutes)
```

## Summary of Approval Methods

| Method | Platform | Requires Config | Notes |
|--------|----------|----------------|-------|
| **Native OS Dialog** | macOS/Windows | No | Auto-disabled when Slack enabled |
| **File-Based (CLI)** | All | No | Always enabled, prints to logs |
| **Slack** | All | Yes (token) | Disables native dialogs when enabled |

## Next Steps

- [Slack Webhook Setup](slack-setup.md) - Configure Slack interactive buttons
- [Configuration Reference](configuration.md) - Detailed configuration options
