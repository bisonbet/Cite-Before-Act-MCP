# Webex Teams Bot Setup Guide

This guide will walk you through setting up a Webex Teams bot for approval notifications with Cite-Before-Act MCP.

## Prerequisites

- Webex account (free tier works fine)
- Public HTTPS endpoint (use ngrok for development, or deploy to cloud)
- Python 3.8+ with webexteamssdk installed

## Architecture Overview

Webex bots work via webhooks:
1. **Bot sends adaptive card** with Approve/Reject buttons
2. **User clicks button** → Webex creates an `attachmentAction`
3. **Webhook receives event** → Your server processes the approval
4. **Approval communicated to MCP server** via file-based IPC

**Note**: Like Slack, Webex uses simple webhooks - no persistent connection required.

## Step 1: Create a Webex Bot

### 1.1 Create Bot Account

1. Go to [Webex for Developers](https://developer.webex.com/my-apps)
2. Sign in with your Webex account
3. Click **Create a New App**
4. Select **Create a Bot**
5. Fill in the details:
   - **Bot name**: `Cite-Before-Act Approval Bot`
   - **Bot username**: `cite-before-act-bot` (must be unique)
   - **Icon**: Upload an icon (512x512 px required)
   - **App Hub Description**: `Bot for approving MCP tool actions`
6. Click **Add Bot**

### 1.2 Save Bot Credentials

After creating the bot, you'll see:
- **Bot's Access Token** - This is your `WEBEX_BOT_TOKEN`
- **Bot Username** - The bot's email address

**CRITICAL**: Copy the access token immediately - you won't be able to retrieve it later!

If you lose it:
1. Go to your bot in [My Apps](https://developer.webex.com/my-apps)
2. Click **Regenerate Access Token**
3. Update your `.env` file with the new token

## Step 2: Find Room/Space ID or Email

You need to tell the bot where to send approval requests. You have two options:

### Option A: Send to a Room/Space

#### 2.1 Create or Use Existing Space

1. Open Webex Teams app
2. Create a new space or use an existing one
3. Add your bot to the space:
   - Click the space name → **People** → **Add people**
   - Search for your bot's username (from Step 1)
   - Add the bot

#### 2.2 Get Room ID

You can get the room ID programmatically:

```python
from webexteamssdk import WebexTeamsAPI

api = WebexTeamsAPI(access_token="YOUR_BOT_TOKEN")

# List all rooms the bot is in
rooms = api.rooms.list()
for room in rooms:
    print(f"Room: {room.title} - ID: {room.id}")
```

Or use the Webex API directly:
```bash
curl -X GET https://webexapis.com/v1/rooms \
  -H "Authorization: Bearer YOUR_BOT_TOKEN"
```

Copy the Room ID and use it as `WEBEX_ROOM_ID`.

### Option B: Send Direct Messages to a User

Instead of a room, you can send approvals directly to a specific person:

1. Get the person's Webex email address
2. Use it as `WEBEX_PERSON_EMAIL` in your `.env` file

**Note**: You can only send messages to people who have interacted with the bot before, or are in the same organization.

## Step 3: Create Webhook for Attachment Actions

The bot needs a webhook to receive button click events.

### 3.1 Start Your Webhook Server

Make sure your server is running and publicly accessible:

**Development (with ngrok):**
```bash
# Terminal 1 - Start webhook server
export ENABLE_WEBEX=true
export WEBEX_BOT_TOKEN=your-bot-token
export SECURITY_MODE=local
python examples/unified_webhook_server.py

# Terminal 2 - Start ngrok
ngrok http 3000
```

Copy your ngrok URL (e.g., `https://abc123.ngrok.io`)

**Production:**
Deploy your server to a cloud provider with HTTPS enabled.

### 3.2 Create the Webhook

You can create the webhook programmatically or via the API.

#### Method A: Using Python

```python
from webexteamssdk import WebexTeamsAPI

api = WebexTeamsAPI(access_token="YOUR_BOT_TOKEN")

# Create webhook for attachment actions
webhook = api.webhooks.create(
    name="Approval Actions Webhook",
    targetUrl="https://your-url.ngrok.io/webex/interactive",
    resource="attachmentActions",
    event="created"
)

print(f"Webhook created: {webhook.id}")
```

#### Method B: Using curl

```bash
curl -X POST https://webexapis.com/v1/webhooks \
  -H "Authorization: Bearer YOUR_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Approval Actions Webhook",
    "targetUrl": "https://your-url.ngrok.io/webex/interactive",
    "resource": "attachmentActions",
    "event": "created"
  }'
```

#### Method C: Automatic (Handled by Code)

The WebexHandler includes a `create_webhook()` method that you can call:

```python
from cite_before_act.webex.handlers import WebexHandler

handler = WebexHandler(access_token="YOUR_BOT_TOKEN")
webhook_id = handler.create_webhook(
    target_url="https://your-url.ngrok.io/webex/interactive",
    name="Approval Actions Webhook"
)
```

### 3.3 Verify Webhook

List your webhooks to verify:

```python
from webexteamssdk import WebexTeamsAPI

api = WebexTeamsAPI(access_token="YOUR_BOT_TOKEN")
webhooks = api.webhooks.list()

for wh in webhooks:
    print(f"Name: {wh.name}")
    print(f"URL: {wh.targetUrl}")
    print(f"Resource: {wh.resource}")
    print(f"Event: {wh.event}")
    print(f"Status: {wh.status}")
    print("---")
```

## Step 4: Configure Cite-Before-Act MCP

### 4.1 Set Environment Variables

Add to your `.env` file:

```bash
# Enable Webex
ENABLE_WEBEX=true

# Webex Bot Token
WEBEX_BOT_TOKEN=your-bot-access-token

# Choose ONE of the following:
# Option A: Send to a room/space
WEBEX_ROOM_ID=your-room-id

# Option B: Send direct messages to a user
# WEBEX_PERSON_EMAIL=user@example.com
```

### 4.2 Install Dependencies

```bash
pip install webexteamssdk
```

### 4.3 Run the Webhook Server

The unified webhook server supports multiple platforms:

```bash
# Enable Webex (and optionally other platforms)
export ENABLE_WEBEX=true
export ENABLE_SLACK=false  # Optional
export ENABLE_TEAMS=false  # Optional

python examples/unified_webhook_server.py
```

Server will run on port 3000 by default.

## Step 5: Test the Integration

1. Make sure your webhook server is running
2. Make sure ngrok is running (for development)
3. Make sure the bot is added to the Webex space (if using room)
4. Run an MCP tool that requires approval
5. You should receive an adaptive card in Webex with Approve/Reject buttons
6. Click a button - the approval should be processed

### Test Message

You can send a test approval request:

```python
from cite_before_act.webex.client import WebexClient

client = WebexClient(
    access_token="YOUR_BOT_TOKEN",
    room_id="YOUR_ROOM_ID"  # or person_email="user@example.com"
)

client.send_approval_request(
    approval_id="test-123",
    tool_name="test_tool",
    description="This is a test approval request",
    arguments={"arg1": "value1"}
)
```

## Step 6: Update Webhook URL (When Changing ngrok)

If you're using ngrok for development, the URL changes each time you restart ngrok. You need to update the webhook:

### Delete Old Webhook

```python
from webexteamssdk import WebexTeamsAPI

api = WebexTeamsAPI(access_token="YOUR_BOT_TOKEN")

# List webhooks
webhooks = api.webhooks.list()
for wh in webhooks:
    if "attachmentActions" in wh.resource:
        print(f"Deleting webhook: {wh.id}")
        api.webhooks.delete(wh.id)
```

### Create New Webhook

Follow Step 3.2 again with your new ngrok URL.

**Pro Tip**: Use a custom ngrok domain (paid feature) or deploy to a cloud provider with a stable URL to avoid this hassle.

## Troubleshooting

### Bot doesn't send messages

**Check:**
- `WEBEX_BOT_TOKEN` is correct
- Bot has access to the room/space (check if bot is added)
- If using `WEBEX_PERSON_EMAIL`, verify the email is correct
- Check webhook server logs for errors

**Test:**
```python
from webexteamssdk import WebexTeamsAPI
api = WebexTeamsAPI(access_token="YOUR_TOKEN")

# Test API connection
me = api.people.me()
print(f"Bot name: {me.displayName}")

# List rooms
rooms = api.rooms.list()
for room in rooms:
    print(f"Room: {room.title}")
```

### Webhook not receiving events

**Check:**
- Webhook URL is correct and publicly accessible
- URL uses HTTPS (required by Webex)
- Webhook is for resource `attachmentActions` and event `created`
- Webhook status is `active`

**Test webhook:**
```bash
curl https://your-url/webex/interactive
# Should return 200 or 404, but not connection refused
```

**Check webhook status:**
```python
api = WebexTeamsAPI(access_token="YOUR_TOKEN")
webhooks = api.webhooks.list()
for wh in webhooks:
    print(f"Status: {wh.status}")
```

### "Invalid access token" errors

**Check:**
- Token hasn't expired (regenerate if needed)
- Token is for a bot, not a personal access token
- Token has `spark:all` scope (bot tokens have this by default)

**Regenerate token:**
1. Go to [My Apps](https://developer.webex.com/my-apps)
2. Click on your bot
3. Click **Regenerate Access Token**
4. Update `.env` file

### Adaptive card doesn't show buttons

**Check:**
- Using correct adaptive card format (see WebexClient code)
- Card version is 1.3 or lower (Webex supports up to 1.3)
- `Action.Submit` is used for buttons (not `Action.Execute` which is Teams-specific)

### Approval response not processed

**Check:**
- Webhook server is receiving the POST request (check logs)
- Attachment action ID is valid
- File is being written to `/tmp/cite-before-act-webex-approval-{id}.json`
- MCP server's cleanup task is reading the file

**Debug:**
```bash
# Check for approval files
ls -la /tmp/cite-before-act-webex-approval-*.json

# Watch in real-time
watch -n 1 'ls -la /tmp/cite-before-act-webex-approval-*.json'
```

## Common Issues and Solutions

### Issue: ngrok URL changes every restart

**Solution:**
- Use ngrok paid plan for reserved domains
- Deploy to cloud provider (Heroku, AWS, Azure, GCP)
- Use a tunnel service with stable URLs

### Issue: Can't send to specific person

**Solution:**
- Person must have interacted with bot first, or
- Be in same organization, or
- Use a room/space instead

### Issue: Webhook keeps getting deleted

**Solution:**
- Webex automatically deletes webhooks that fail repeatedly
- Fix your server errors
- Verify URL is accessible
- Re-create webhook after fixing issues

## Security Considerations

1. **Keep Bot Token Secret**: Never commit to version control
2. **Use HTTPS**: Webex requires HTTPS for webhooks
3. **Validate Webhook Data**: Verify attachment action IDs
4. **Rate Limiting**: Be mindful of API rate limits
5. **Monitor Logs**: Watch for unusual activity

## Production Deployment Checklist

- [ ] Deploy webhook server to cloud with HTTPS
- [ ] Create webhook with production URL
- [ ] Set `SECURITY_MODE=production`
- [ ] Configure proper WSGI server (gunicorn, waitress)
- [ ] Set up log monitoring
- [ ] Document token rotation procedure
- [ ] Test failover scenarios
- [ ] Monitor webhook health

## API Rate Limits

Webex has rate limits:
- **Messages**: 10,000 per 10 minutes per bot
- **Webhooks**: 100 per 10 minutes per bot
- **Attachment Actions**: No specific limit, but general API limits apply

For most approval use cases, you won't hit these limits.

## Additional Resources

- [Webex for Developers](https://developer.webex.com/)
- [Buttons and Cards Guide](https://developer.webex.com/docs/buttons-and-cards)
- [Adaptive Cards Designer](https://adaptivecards.io/designer/)
- [Webex Python SDK](https://github.com/CiscoDevNet/webexteamssdk)
- [Webhooks API Reference](https://developer.webex.com/docs/api/v1/webhooks)

## Next Steps

- [General Setup Guide](../README.md)
- [Slack Setup Guide](./SLACK_SETUP.md)
- [Teams Setup Guide](./TEAMS_SETUP.md)
- [Architecture Documentation](./ARCHITECTURE.md)
