# Webex Teams Bot Setup Guide

This guide will walk you through setting up a Webex Teams bot for approval notifications with Cite-Before-Act MCP.

## Prerequisites

- Webex account (free tier works fine)
- Public HTTPS endpoint (use ngrok for development, or deploy to cloud)
- Python 3.8+ (Python 3.10+ recommended for better compatibility)
- `webexteamssdk` package installed

**Note**: This guide uses the official `webexteamssdk` package from CiscoDevNet, which is the recommended SDK for Webex Teams API integration.

## Architecture Overview

Webex bots work via webhooks:
1. **Bot sends adaptive card** with Approve/Reject buttons to a Webex room or user
2. **User clicks button** → Webex creates an `attachmentAction` event
3. **Webhook receives event** → Your webhook server processes the approval
4. **Approval response written** → File-based IPC (`/tmp/cite-before-act-webex-approval-{id}.json`)
5. **MCP server reads file** → Approval decision is processed

**Note**: Like Slack, Webex uses simple HTTP webhooks - no persistent connection required. The webhook server receives POST requests when users interact with buttons.

## Step 1: Create a Webex Bot

### 1.1 Create Bot Account

1. Go to [Webex for Developers](https://developer.webex.com/my-apps)
2. Sign in with your Webex account
3. Click **Create a New App**
4. Select **Create a Bot**
5. Fill in the details:
   - **Bot name**: `Cite-Before-Act Approval Bot`
   - **Bot username**: `cite-before-act-bot` (must be unique)
   - **Icon**: Upload an icon (recommended: 512x512 px or larger, square format)
   - **App Hub Description**: `Bot for approving MCP tool actions`
6. Click **Add Bot**

### 1.2 Save Bot Credentials

After creating the bot, you'll see:
- **Bot's Access Token** - This is your `WEBEX_BOT_TOKEN` (starts with something like `Y2lzY29...`)
- **Bot Username** - The bot's email address (e.g., `cite-before-act-bot@webex.bot`)

**CRITICAL**: Copy the access token immediately - you won't be able to retrieve it later! The token is only shown once during bot creation.

**If you lose the token:**
1. Go to your bot in [My Apps](https://developer.webex.com/my-apps)
2. Click on your bot name
3. Look for the **Access Token** section
4. Click **Regenerate Access Token** (or **Copy** if it's still visible)
5. **Important**: Regenerating creates a new token and invalidates the old one
6. Copy the new token and update your `.env` file immediately
7. Restart your webhook server and MCP server to use the new token

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

1. Get the person's Webex email address (their Webex account email)
2. Use it as `WEBEX_PERSON_EMAIL` in your `.env` file

**Important Notes**:
- The person must have interacted with the bot at least once (e.g., sent a message to the bot)
- OR they must be in the same organization as the bot
- For testing, it's often easier to use a room/space instead
- If using `WEBEX_PERSON_EMAIL`, do NOT set `WEBEX_ROOM_ID` (only one should be set)

## Step 3: Create Webhook for Attachment Actions

The bot needs a webhook to receive button click events. When a user clicks a button on an adaptive card, Webex sends a webhook POST request to your server with the attachment action details.

**How it works:**
1. User clicks Approve/Reject button on adaptive card
2. Webex creates an `attachmentAction` resource
3. Webex sends webhook POST to your configured URL with payload like:
   ```json
   {
     "id": "webhook-id",
     "name": "Approval Actions Webhook",
     "resource": "attachmentActions",
     "event": "created",
     "data": {
       "id": "attachment-action-id-here"
     }
   }
   ```
4. Your webhook server extracts the attachment action ID from `data.id`
5. Your server calls Webex API (`api.attachment_actions.get(action_id)`) to get full action details
6. The full action object contains `inputs` with your button data (`approval_id`, `action`, etc.)
7. Approval decision is written to file (`/tmp/cite-before-act-webex-approval-{id}.json`) for MCP server to process

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

You can create the webhook programmatically or via the API. The webhook must listen for `attachmentActions` resource with `created` event.

#### Method A: Using Python

```python
from webexteamssdk import WebexTeamsAPI

api = WebexTeamsAPI(access_token="YOUR_BOT_TOKEN")

# Create webhook for attachment actions
# This webhook will fire when users click buttons on adaptive cards
webhook = api.webhooks.create(
    name="Approval Actions Webhook",
    targetUrl="https://your-url.ngrok.io/webex/interactive",
    resource="attachmentActions",  # Must be "attachmentActions"
    event="created"                 # Must be "created"
)

print(f"Webhook created: {webhook.id}")
print(f"Webhook URL: {webhook.targetUrl}")
```

**Important**: 
- The `targetUrl` must be publicly accessible via HTTPS
- The endpoint should be `/webex/interactive` (as configured in the unified webhook server)
- Webex will send POST requests to this URL when users click buttons

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

List your webhooks to verify they're set up correctly:

```python
from webexteamssdk import WebexTeamsAPI

api = WebexTeamsAPI(access_token="YOUR_BOT_TOKEN")
webhooks = api.webhooks.list()

for wh in webhooks:
    print(f"Name: {wh.name}")
    print(f"URL: {wh.targetUrl}")
    print(f"Resource: {wh.resource}")
    print(f"Event: {wh.event}")
    print(f"Status: {wh.status}")  # Should be "active"
    print(f"ID: {wh.id}")
    print("---")
```

**What to check**:
- `resource` should be `"attachmentActions"`
- `event` should be `"created"`
- `status` should be `"active"` (if it's `"inactive"`, there may be connectivity issues)
- `targetUrl` should match your webhook server URL

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

Install the required Webex SDK:

```bash
pip install "webexteamssdk>=1.6.0"
```

**Important PyJWT Version Conflict:**

The `webexteamssdk` package depends on an outdated version of PyJWT (1.7.1), which conflicts with the newer PyJWT version (2.10.1+) required by both `mcp` and `botframework-connector` (if using Teams). After installing `webexteamssdk`, you must upgrade PyJWT:

```bash
pip install "webexteamssdk>=1.6.0"
pip install "pyjwt[crypto]>=2.10.1"
```

This will:
1. First install `webexteamssdk` and its dependencies (including old PyJWT 1.7.1)
2. Then upgrade PyJWT to 2.10.1+ with cryptographic support, which is compatible with both Webex SDK and other packages

**Or install all dependencies from requirements.txt** (recommended - handles conflicts automatically):

```bash
pip install -r requirements.txt
```

**Note**: The `webexteamssdk` package is the official Cisco DevNet SDK for Webex Teams API integration. Despite the PyJWT version mismatch in its declared dependencies, it works correctly with PyJWT 2.10.1+.

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

1. **Start the webhook server** (see Step 3.1)
2. **Verify ngrok is running** (for development) and copy the HTTPS URL
3. **Create the webhook** (see Step 3.2) with your ngrok URL
4. **Add the bot to a Webex space** (if using `WEBEX_ROOM_ID`):
   - Open Webex Teams app
   - Go to your space
   - Click space name → **People** → **Add people**
   - Search for your bot's username and add it
5. **Trigger an approval request**:
   - Run an MCP tool that requires approval (e.g., `write_file`, `create_repository`)
   - The Cite-Before-Act middleware should detect it as mutating
6. **Check Webex for approval card**:
   - You should receive an adaptive card in Webex with Approve/Reject buttons
   - The card shows the tool name, description, and arguments
7. **Test approval/rejection**:
   - Click **Approve** or **Reject** button
   - Check webhook server logs for "Webex approval response received"
   - Verify the approval file is created in `/tmp/`
   - The MCP tool should proceed (if approved) or be rejected (if rejected)

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
- Webhook URL is correct and publicly accessible (test with `curl` or browser)
- URL uses HTTPS (required by Webex - HTTP will be rejected)
- Webhook is for resource `attachmentActions` and event `created`
- Webhook status is `active` (not `inactive`)
- Your webhook server is running and accessible
- Firewall/network allows incoming POST requests

**Test webhook endpoint:**
```bash
# Test if endpoint is accessible
curl -X POST https://your-url/webex/interactive \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
# Should return a JSON response (even if error), not "connection refused"
# A 400 Bad Request is normal without proper webhook payload
```

**Check webhook status:**
```python
from webexteamssdk import WebexTeamsAPI

api = WebexTeamsAPI(access_token="YOUR_TOKEN")
webhooks = api.webhooks.list()
for wh in webhooks:
    if wh.resource == "attachmentActions":
        print(f"Status: {wh.status}")
        print(f"URL: {wh.targetUrl}")
        if wh.status != "active":
            print("⚠️ Webhook is not active! Check your server connectivity.")
```

**Common issues:**
- If webhook status becomes `inactive`, Webex couldn't reach your server. Common causes:
  - Server is down or unreachable
  - Firewall blocking incoming connections
  - URL changed (e.g., ngrok restarted with new URL)
  - SSL/TLS certificate issues (HTTPS required)
- Webex automatically deletes webhooks that fail repeatedly (usually after multiple failed delivery attempts over several hours)
- If your webhook disappears, recreate it with the correct URL

### "Invalid access token" errors

**Check:**
- Token is correct (no extra spaces, copied completely)
- Token is for a bot, not a personal access token (bot tokens start with `Y2lzY29...`)
- Token hasn't been regenerated (if you regenerated it, old token is invalid)
- Token has proper scopes (bot tokens have `spark:all` by default)

**Test token validity:**
```python
from webexteamssdk import WebexTeamsAPI
from webexteamssdk.exceptions import ApiError

try:
    api = WebexTeamsAPI(access_token="YOUR_TOKEN")
    me = api.people.me()
    print(f"✅ Token valid! Bot name: {me.displayName}")
except ApiError as e:
    print(f"❌ Token invalid: {e}")
```

**Regenerate token:**
1. Go to [My Apps](https://developer.webex.com/my-apps)
2. Click on your bot name
3. Look for the **Access Token** section
4. Click **Regenerate Access Token** (or **Copy** if still visible)
5. **Important**: The old token will be invalidated immediately
6. **Immediately** update your `.env` file with the new token
7. Restart your webhook server and MCP server to use the new token
8. Verify the bot can send messages after token update

### Adaptive card doesn't show buttons

**Check:**
- Using correct adaptive card format (see `cite_before_act/webex/client.py`)
- Card version is `1.3` or lower (Webex supports up to 1.3, code uses 1.3)
- `Action.Submit` is used for buttons (not `Action.Execute` which is Microsoft Teams-specific)
- Card structure follows Webex's adaptive card requirements
- Buttons are in the `actions` array of the card

**Verify card format:**
The card should have this structure:
```json
{
  "type": "AdaptiveCard",
  "version": "1.3",
  "body": [...],
  "actions": [
    {
      "type": "Action.Submit",
      "title": "✅ Approve",
      "data": {
        "action": "approve",
        "approval_id": "..."
      }
    }
  ]
}
```

**Note**: Webex supports adaptive cards version 1.3. Newer versions (1.4+) are not supported by Webex. The code uses version 1.3 to ensure compatibility.

### Approval response not processed

**Check:**
- Webhook server is receiving the POST request (check server logs for incoming requests)
- Webhook handler is processing the attachment action (check for "Webex approval response received" in logs)
- Attachment action ID is valid (webhook payload contains `data.id`)
- File is being written to `/tmp/cite-before-act-webex-approval-{approval_id}.json`
- MCP server's file watcher is reading the file (check MCP server logs)
- Approval ID matches between request and response

**Debug webhook payload:**
Add logging to see what Webex is sending:
```python
# In your webhook handler, add:
print(f"Webhook payload: {json.dumps(webhook_data, indent=2)}")
```

**Debug file-based approval:**
```bash
# Check for approval files
ls -la /tmp/cite-before-act-webex-approval-*.json

# Watch in real-time (Linux/macOS)
watch -n 1 'ls -la /tmp/cite-before-act-webex-approval-*.json'

# Or manually check (macOS/Windows)
ls -la /tmp/cite-before-act-webex-approval-*.json

# View file contents (replace {approval_id} with actual ID)
cat /tmp/cite-before-act-webex-approval-{approval_id}.json

# Monitor for new files (Linux/macOS)
watch -n 0.5 'ls -lt /tmp/cite-before-act-webex-approval-*.json 2>/dev/null | head -5'
```

**Note**: On Windows, the `/tmp` directory may not exist. The code uses `/tmp` which maps to a temporary directory on Windows. If files aren't appearing, check your system's temp directory or configure a custom path.

**Expected file format:**
```json
{
  "approval_id": "abc123...",
  "approved": true,
  "platform": "webex",
  "timestamp": 1704110400.0
}
```

**Note**: The `timestamp` is a Unix timestamp (float), not an ISO string. The file is written to `/tmp/cite-before-act-webex-approval-{approval_id}.json`.

## Common Issues and Solutions

### Issue: ngrok URL changes every restart

**Problem**: Free ngrok URLs change each time you restart ngrok, requiring webhook updates.

**Solution:**
- **Option 1**: Use ngrok paid plan for reserved domains (stable URL)
- **Option 2**: Deploy to cloud provider (Heroku, AWS, Azure, GCP, Railway, Render)
- **Option 3**: Use a tunnel service with stable URLs (Cloudflare Tunnel, localtunnel with custom domain)
- **Option 4**: Create a script to automatically update webhook URL when ngrok restarts

**Quick fix**: Delete old webhook and create new one with updated URL (see Step 6).

### Issue: Can't send to specific person

**Solution:**
- Person must have interacted with bot first, or
- Be in same organization, or
- Use a room/space instead

### Issue: Webhook keeps getting deleted

**Problem**: Webex automatically deletes webhooks that fail to deliver events repeatedly.

**Solution:**
- **Fix server errors**: Check webhook server logs for errors
- **Verify URL is accessible**: Test with `curl` to ensure endpoint responds
- **Check HTTPS**: Webex requires HTTPS - ensure your URL uses `https://`
- **Monitor webhook status**: Regularly check webhook status (see Step 3.3)
- **Re-create webhook**: After fixing issues, delete inactive webhook and create a new one
- **Use stable URL**: Avoid URL changes (see "ngrok URL changes" issue above)
- **Check firewall**: Ensure your server accepts incoming POST requests on the webhook endpoint

## Security Considerations

1. **Keep Bot Token Secret**: Never commit to version control
2. **Use HTTPS**: Webex requires HTTPS for webhooks
3. **Validate Webhook Data**: Verify attachment action IDs
4. **Rate Limiting**: Be mindful of API rate limits
5. **Monitor Logs**: Watch for unusual activity

## Production Deployment Checklist

- [ ] Deploy webhook server to cloud with HTTPS (Azure App Service, AWS, GCP, Heroku, Railway, Render)
- [ ] Create webhook with production URL (stable, not ngrok)
- [ ] Set `SECURITY_MODE=production` in environment variables
- [ ] Configure proper WSGI server (gunicorn, waitress, uwsgi)
- [ ] Set up log monitoring and alerting
- [ ] Document token rotation procedure
- [ ] Test failover scenarios
- [ ] Monitor webhook health (check status regularly)
- [ ] Set up health check endpoint monitoring (`/health`)
- [ ] Configure rate limiting if needed (handled by `SECURITY_MODE=production`)
- [ ] Document webhook URL update procedure
- [ ] Test approval flow end-to-end in production environment

## API Rate Limits

Webex has rate limits that apply to API calls:
- **Messages**: 10,000 per 10 minutes per bot
- **Webhooks**: 100 create/update/delete operations per 10 minutes per bot
- **Attachment Actions**: No specific limit, but subject to general API rate limits
- **General API**: 10 requests per second per bot (burst up to 20)

For most approval use cases, you won't hit these limits. If you do:
- You'll receive HTTP 429 (Too Many Requests) responses
- Implement exponential backoff retry logic
- Consider batching operations if sending many approvals

**Note**: 
- Rate limits are per bot token, so each bot has its own quota
- If you hit rate limits, you'll receive HTTP 429 (Too Many Requests) responses
- The unified webhook server includes basic rate limiting in production mode
- For high-volume scenarios, implement exponential backoff retry logic

## Additional Resources

- [Webex for Developers](https://developer.webex.com/) - Main developer portal
- [Webex REST API Documentation](https://developer.webex.com/docs/api/v1) - Complete API reference
- [Buttons and Cards Guide](https://developer.webex.com/docs/buttons-and-cards) - How to create interactive cards
- [Adaptive Cards Designer](https://adaptivecards.io/designer/) - Visual card designer (use version 1.3 for Webex)
- [Webex Python SDK (webexteamssdk)](https://github.com/CiscoDevNet/webexteamssdk) - Official Python SDK
- [Webhooks API Reference](https://developer.webex.com/docs/api/v1/webhooks) - Webhook setup and management
- [Attachment Actions API](https://developer.webex.com/docs/api/v1/attachment-actions) - How attachment actions work
- [Webex Bot Getting Started](https://developer.webex.com/docs/bots) - Bot development guide

## Next Steps

- [General Setup Guide](../README.md)
- [Slack Setup Guide](./SLACK_SETUP.md)
- [Teams Setup Guide](./TEAMS_SETUP.md)
- [Architecture Documentation](./ARCHITECTURE.md)
