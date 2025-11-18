# Multi-Platform Approval System

Cite-Before-Act MCP now supports approval notifications via **Slack**, **Webex Teams**, and **Microsoft Teams**!

## Overview

The approval system has been expanded to support three collaboration platforms, all working through a unified webhook server. You can enable one, two, or all three platforms simultaneously.

### Key Features

✅ **Unified Webhook Server** - Single server handles all platforms
✅ **Multi-Platform Support** - Send approvals to Slack, Webex, and Teams
✅ **Parallel Approvals** - First approval from any platform wins
✅ **Adaptive Cards** - Beautiful interactive buttons in all platforms
✅ **Shared Configuration** - Consistent environment variable setup
✅ **Local Fallback** - Still works without any platform configured

## Platform Comparison

| Feature | Slack | Webex | Teams |
|---------|-------|-------|-------|
| **Setup Complexity** | Easy | Easy | Complex |
| **Card Format** | Block Kit | Adaptive Cards | Adaptive Cards |
| **Webhook Type** | Simple | Simple | Bot Framework |
| **Requires Cloud Service** | No | No | Yes (Azure) |
| **Authentication** | Token + Secret | Token | App ID + Password |
| **Best For** | Small teams | Cisco orgs | Enterprise |

## Quick Start

### 1. Choose Your Platform(s)

You can enable any combination:

```bash
# Enable just one
export ENABLE_SLACK=true

# Enable multiple
export ENABLE_SLACK=true
export ENABLE_WEBEX=true
export ENABLE_TEAMS=true
```

### 2. Install Dependencies

```bash
# For Slack
pip install slack-sdk

# For Webex
pip install webexteamssdk

# For Teams
pip install botbuilder-core botframework-connector

# Webhook server (required)
pip install flask
```

### 3. Configure Credentials

**Slack:**
```bash
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_CHANNEL=#approvals
```

**Webex:**
```bash
WEBEX_BOT_TOKEN=your-webex-token
WEBEX_ROOM_ID=your-room-id
# OR
WEBEX_PERSON_EMAIL=user@example.com
```

**Teams:**
```bash
TEAMS_APP_ID=your-app-id
TEAMS_APP_PASSWORD=your-app-password
```

### 4. Run Unified Webhook Server

```bash
python examples/unified_webhook_server.py
```

### 5. Configure Platform Webhooks

Each platform needs to know your webhook URL:

- **Slack**: `https://your-url/slack/interactive`
- **Webex**: `https://your-url/webex/interactive`
- **Teams**: `https://your-url/api/messages`

## Architecture

### How It Works

```
┌─────────────────────────────────────────────────────────┐
│                     MCP Server                          │
│                                                         │
│  ┌───────────────────────────────────────────────────┐ │
│  │          ApprovalManager                          │ │
│  │                                                   │ │
│  │  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐│ │
│  │  │ Slack  │  │ Webex  │  │ Teams  │  │ Local  ││ │
│  │  │ Client │  │ Client │  │ Client │  │Approval││ │
│  │  └────────┘  └────────┘  └────────┘  └────────┘│ │
│  │       ↓           ↓           ↓           ↓     │ │
│  │  All methods run in PARALLEL                    │ │
│  │  First approval from ANY source wins            │ │
│  └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
         ↓                ↓                ↓
   Sends cards    Sends cards      Sends cards
         ↓                ↓                ↓
┌───────────────┐  ┌──────────┐  ┌────────────────┐
│     Slack     │  │  Webex   │  │  Teams (Azure) │
└───────────────┘  └──────────┘  └────────────────┘
         ↓                ↓                ↓
   User clicks    User clicks      User clicks
   Approve/Reject Approve/Reject   Approve/Reject
         ↓                ↓                ↓
┌─────────────────────────────────────────────────────────┐
│         Unified Webhook Server (Flask)                  │
│                                                         │
│  /slack/interactive     - Slack endpoint               │
│  /webex/interactive     - Webex endpoint               │
│  /api/messages          - Teams endpoint               │
│                                                         │
│  Writes approval to:                                   │
│  /tmp/cite-before-act-{platform}-approval-{id}.json    │
└─────────────────────────────────────────────────────────┘
         ↓
   MCP Server cleanup task reads file
         ↓
   Approval resolved → Tool executes (if approved)
```

### File-Based IPC

All platforms communicate approval decisions via JSON files:

```bash
/tmp/cite-before-act-slack-approval-{approval_id}.json
/tmp/cite-before-act-webex-approval-{approval_id}.json
/tmp/cite-before-act-teams-approval-{approval_id}.json
```

This allows the webhook server (separate process) to communicate with the MCP server.

## Configuration Reference

### Environment Variables

#### Common
```bash
APPROVAL_TIMEOUT_SECONDS=300      # Default: 5 minutes
USE_LOCAL_APPROVAL=true           # Enable local fallback
USE_GUI_APPROVAL=true             # Native OS dialogs (when no platform)
SECURITY_MODE=local|production    # Webhook server mode
PORT=3000                         # Webhook server port
```

#### Slack
```bash
ENABLE_SLACK=true
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL=#channel-name       # or channel ID (C...) or user ID (U...)
SLACK_SIGNING_SECRET=...          # Required for production mode
```

#### Webex
```bash
ENABLE_WEBEX=true
WEBEX_BOT_TOKEN=...
WEBEX_ROOM_ID=...                 # Room/space ID
# OR
WEBEX_PERSON_EMAIL=user@example.com
```

#### Teams
```bash
ENABLE_TEAMS=true
TEAMS_APP_ID=...                  # Azure App ID
TEAMS_APP_PASSWORD=...            # Azure App Password
TEAMS_SERVICE_URL=...             # Optional, default works for most
TEAMS_CONVERSATION_ID=...         # Optional, auto-detected
TEAMS_TENANT_ID=...               # Optional
```

## New Files and Modules

### Core Implementation

```
cite_before_act/
├── webex/
│   ├── __init__.py
│   ├── client.py         # WebexClient - sends adaptive cards
│   └── handlers.py       # WebexHandler - processes button clicks
├── teams/
│   ├── __init__.py
│   ├── client.py         # TeamsClient - sends via Bot Framework
│   ├── handlers.py       # TeamsHandler - processes invoke activities
│   └── adapter.py        # Bot Framework adapter setup
└── approval.py           # Updated to support all platforms
```

### Webhook Server

```
examples/
├── unified_webhook_server.py    # NEW: Handles all three platforms
└── slack_webhook_server.py      # LEGACY: Slack only (still works)
```

### Documentation

```
docs/
├── TEAMS_SETUP.md               # Complete Teams setup guide
├── WEBEX_SETUP.md               # Complete Webex setup guide
└── MULTI_PLATFORM_APPROVALS.md  # This file
```

### Configuration

```
config/settings.py               # Updated with WebexConfig, TeamsConfig
requirements.txt                 # Updated with new dependencies
```

## Usage Examples

### Enable Multiple Platforms

```bash
# .env file
ENABLE_SLACK=true
ENABLE_WEBEX=true
ENABLE_TEAMS=true

# Slack credentials
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL=#approvals

# Webex credentials
WEBEX_BOT_TOKEN=...
WEBEX_ROOM_ID=...

# Teams credentials
TEAMS_APP_ID=...
TEAMS_APP_PASSWORD=...
```

When an approval is needed:
1. Card sent to Slack channel
2. Card sent to Webex room
3. Card sent to Teams channel
4. **First person to click Approve/Reject** resolves the approval
5. Other platforms' cards still work but become no-ops

### Enable Just Webex

```bash
ENABLE_SLACK=false
ENABLE_WEBEX=true
ENABLE_TEAMS=false

WEBEX_BOT_TOKEN=your-token
WEBEX_ROOM_ID=your-room-id
```

### Production Deployment

```bash
# Use production security mode
export SECURITY_MODE=production

# Enable desired platforms
export ENABLE_SLACK=true
export ENABLE_WEBEX=true

# Set credentials
export SLACK_BOT_TOKEN=...
export SLACK_SIGNING_SECRET=...  # Required in production
export WEBEX_BOT_TOKEN=...
export WEBEX_ROOM_ID=...

# Run with production WSGI server
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:3000 examples.unified_webhook_server:app
```

## Detailed Setup Guides

- **Slack Setup**: See [docs/SLACK_SETUP.md](./SLACK_SETUP.md) (existing)
- **Webex Setup**: See [docs/WEBEX_SETUP.md](./WEBEX_SETUP.md) (new!)
- **Teams Setup**: See [docs/TEAMS_SETUP.md](./TEAMS_SETUP.md) (new!)

## Troubleshooting

### No approvals received

**Check:**
1. Webhook server is running
2. Platform(s) enabled in environment
3. Credentials are correct
4. Webhook URLs configured in each platform
5. Bot added to channels/rooms/chats

### Approvals work but MCP doesn't see them

**Check:**
1. Files being written to `/tmp/cite-before-act-{platform}-approval-*.json`
2. MCP server cleanup task is running
3. File permissions allow reading

**Debug:**
```bash
# Watch approval files in real-time
watch -n 1 'ls -la /tmp/cite-before-act-*-approval-*.json'
```

### Multiple platforms sending, only one works

**Check:**
- All platforms have webhooks configured
- Webhook URLs are correct and accessible
- Check webhook server logs for which platforms are receiving events

## Security Notes

### Production Mode

In production mode, the webhook server enforces:
- **Slack**: HMAC-SHA256 signature verification
- **Webex**: Attachment action ID validation
- **Teams**: Bot Framework JWT token verification (automatic)
- **All**: Rate limiting, payload size validation, sanitized errors

### Credentials Management

**Never commit credentials to version control!**

Use `.env` file (gitignored):
```bash
# Add to .gitignore
.env
```

For production:
- Use environment variables in cloud platform
- Rotate secrets regularly
- Use secret managers (AWS Secrets Manager, Azure Key Vault, etc.)

## Migration from Slack-Only

If you're currently using Slack only:

1. **Keep existing setup** - It still works!
2. **Install new dependencies** - `pip install webexteamssdk botbuilder-core`
3. **Add new platforms** - Set `ENABLE_WEBEX=true` and/or `ENABLE_TEAMS=true`
4. **Switch to unified server** - Use `unified_webhook_server.py` instead of `slack_webhook_server.py`
5. **Configure webhooks** - Set up Webex/Teams webhooks
6. **Test** - Try sending approvals to verify all platforms work

## FAQ

### Q: Can I use different platforms for different approvals?

**A:** Currently, all enabled platforms receive all approval requests. Future enhancement could add approval routing logic.

### Q: What happens if I click buttons on multiple platforms?

**A:** First click wins - the approval is resolved immediately. Subsequent clicks are ignored (though buttons still work, they just don't change the outcome).

### Q: Do I need all three platforms?

**A:** No! Enable only what you need. Even zero platforms works (local approval only).

### Q: Which platform is easiest to set up?

**A:** Slack and Webex are equally easy (10-15 minutes). Teams requires Azure setup (30-45 minutes).

### Q: Can I use the same webhook server for development and production?

**A:** Yes, but not simultaneously. Use different ports or hosts. Better: use ngrok for dev, cloud deployment for production.

### Q: How do I monitor approvals across platforms?

**A:** Check the webhook server logs - it shows approvals from all platforms with platform identifiers.

## Next Steps

1. Choose your platform(s)
2. Follow the detailed setup guide for each:
   - [Slack Setup](./SLACK_SETUP.md)
   - [Webex Setup](./WEBEX_SETUP.md)
   - [Teams Setup](./TEAMS_SETUP.md)
3. Start the unified webhook server
4. Test with a simple approval
5. Deploy to production!

## Support

For issues or questions:
- Check the detailed setup guides
- Review webhook server logs
- Verify environment variables
- Test endpoints with curl
- Check platform-specific troubleshooting sections

Happy approving! 🎉
