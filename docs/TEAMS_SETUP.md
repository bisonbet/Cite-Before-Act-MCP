# Microsoft Teams Bot Setup Guide

This guide will walk you through setting up a Microsoft Teams bot for approval notifications with Cite-Before-Act MCP.

## Prerequisites

- Azure account with permissions to create App Registrations and Bot Services
- Microsoft Teams workspace where you can add bots
- Public HTTPS endpoint (use ngrok for development, or deploy to cloud)
- Python 3.8+ with botbuilder-core and botframework-connector installed

## Architecture Overview

Unlike Slack and Webex which use simple webhooks, Microsoft Teams requires:
1. **Azure Bot Service** - Manages bot authentication and message routing
2. **App Registration** - Provides App ID and Password for authentication
3. **Messaging Endpoint** - Public HTTPS URL where your bot receives messages
4. **Bot Framework SDK** - Handles bot protocol and adaptive cards

**Important**: Despite being more complex, Teams bots work via webhooks just like Slack/Webex - they don't maintain persistent connections. Teams sends HTTP POST requests to your bot's endpoint.

## Step 1: Create Azure Bot Registration

### 1.1 Register an Application in Azure AD

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory** → **App registrations**
3. Click **New registration**
   - Name: `Cite-Before-Act Approval Bot`
   - Supported account types: `Accounts in any organizational directory (Any Azure AD directory - Multitenant)`
   - Redirect URI: Leave blank for now
4. Click **Register**

### 1.2 Generate Client Secret

1. In your new app registration, go to **Certificates & secrets**
2. Click **New client secret**
   - Description: `Bot password`
   - Expires: Choose your preferred expiration (recommend 12-24 months)
3. Click **Add**
4. **CRITICAL**: Copy the **Value** immediately - you won't be able to see it again!
   - This is your `TEAMS_APP_PASSWORD`
5. Also copy the **Application (client) ID** from the Overview page
   - This is your `TEAMS_APP_ID`

### 1.3 Create Azure Bot

1. In Azure Portal, search for **Azure Bot** service
2. Click **Create** → **Azure Bot**
3. Fill in the details:
   - **Bot handle**: Unique name (e.g., `cite-before-act-bot`)
   - **Subscription**: Your Azure subscription
   - **Resource group**: Create new or use existing
   - **Pricing tier**: Free (F0) is sufficient for testing
   - **Microsoft App ID**: **Use existing app registration**
     - Select the App ID you created in Step 1.1
4. Click **Review + create**, then **Create**

### 1.4 Configure Messaging Endpoint

1. Go to your Azure Bot resource
2. Click **Configuration** in the left menu
3. Set **Messaging endpoint**:
   - For development: `https://your-ngrok-url.ngrok.io/api/messages`
   - For production: `https://your-domain.com/api/messages`
4. Click **Apply**

## Step 2: Add Bot to Microsoft Teams

### 2.1 Enable Teams Channel

1. In your Azure Bot, go to **Channels**
2. Click the **Microsoft Teams** icon
3. Accept the terms and click **Apply**
4. Once enabled, you'll see Teams listed as a channel

### 2.2 Create App Manifest

Create a `teams-app-manifest.zip` file with the following structure:

```
teams-app-manifest/
├── manifest.json
├── color-icon.png  (192x192 px)
└── outline-icon.png  (32x32 px)
```

**manifest.json** (replace `YOUR_APP_ID` with your actual App ID):

```json
{
  "$schema": "https://developer.microsoft.com/en-us/json-schemas/teams/v1.14/MicrosoftTeams.schema.json",
  "manifestVersion": "1.14",
  "version": "1.0.0",
  "id": "YOUR_APP_ID",
  "packageName": "com.example.citebeforeactbot",
  "developer": {
    "name": "Your Organization",
    "websiteUrl": "https://example.com",
    "privacyUrl": "https://example.com/privacy",
    "termsOfUseUrl": "https://example.com/terms"
  },
  "name": {
    "short": "Approval Bot",
    "full": "Cite-Before-Act Approval Bot"
  },
  "description": {
    "short": "Bot for approving MCP tool actions",
    "full": "This bot sends approval requests for mutating operations and receives approve/reject responses via adaptive cards."
  },
  "icons": {
    "outline": "outline-icon.png",
    "color": "color-icon.png"
  },
  "accentColor": "#FFFFFF",
  "bots": [
    {
      "botId": "YOUR_APP_ID",
      "scopes": ["team", "personal", "groupchat"],
      "supportsFiles": false,
      "isNotificationOnly": false,
      "commandLists": [
        {
          "scopes": ["team", "personal", "groupchat"],
          "commands": []
        }
      ]
    }
  ],
  "permissions": [
    "identity",
    "messageTeamMembers"
  ],
  "validDomains": []
}
```

Create simple icon files (or download from [Teams Icons](https://learn.microsoft.com/en-us/microsoftteams/platform/resources/schema/manifest-schema#icons)):
- `color-icon.png`: 192x192 px, full color
- `outline-icon.png`: 32x32 px, white on transparent

Zip the directory:
```bash
cd teams-app-manifest
zip -r ../teams-app-manifest.zip *
```

### 2.3 Upload to Teams

1. Open Microsoft Teams
2. Click **Apps** in the left sidebar
3. Click **Manage your apps** (bottom left)
4. Click **Upload an app** → **Upload a custom app**
5. Select your `teams-app-manifest.zip` file
6. Click **Add** to add the bot to a team/chat

## Step 3: Configure Cite-Before-Act MCP

### 3.1 Set Environment Variables

Add to your `.env` file:

```bash
# Enable Microsoft Teams
ENABLE_TEAMS=true

# Teams Bot Credentials
TEAMS_APP_ID=your-app-id-from-step-1.2
TEAMS_APP_PASSWORD=your-app-password-from-step-1.2

# Optional: Service URL (usually default is fine)
TEAMS_SERVICE_URL=https://smba.trafficmanager.net/amer/

# Optional: Pre-configure conversation (will auto-detect otherwise)
# TEAMS_CONVERSATION_ID=your-channel-or-chat-id
# TEAMS_TENANT_ID=your-tenant-id
```

### 3.2 Install Dependencies

```bash
pip install botbuilder-core botframework-connector
```

### 3.3 Run the Webhook Server

#### For Development (with ngrok):

Terminal 1 - Start the unified webhook server:
```bash
export ENABLE_TEAMS=true
export TEAMS_APP_ID=your-app-id
export TEAMS_APP_PASSWORD=your-app-password
export SECURITY_MODE=local

python examples/unified_webhook_server.py
```

Terminal 2 - Start ngrok:
```bash
ngrok http 3000
```

Copy the ngrok URL and update your Azure Bot's messaging endpoint (Step 1.4).

#### For Production:

```bash
export ENABLE_TEAMS=true
export TEAMS_APP_ID=your-app-id
export TEAMS_APP_PASSWORD=your-app-password
export SECURITY_MODE=production

# For production, use a WSGI server
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:3000 examples.unified_webhook_server:app
```

## Step 4: Get Conversation Reference

The bot needs to know where to send approval requests. This happens automatically when:

1. **You add the bot to a channel/chat** - It receives a conversation update event
2. **You send the bot a message** - It receives the conversation reference
3. **The bot is mentioned in a channel** - It receives the conversation reference

### 4.1 Manual Method (Recommended for Testing)

1. Open Teams and go to the chat/channel where you added the bot
2. Send a message to the bot (e.g., "hello")
3. The bot will store the conversation reference automatically
4. Check the webhook server logs - you should see:
   ```
   📝 Stored Teams conversation reference: 19:xxxxx...
   ```

### 4.2 Find Conversation ID Manually (Optional)

If you want to pre-configure the conversation ID:

1. Open Teams in a web browser
2. Navigate to your team/channel
3. Look at the URL - it contains the conversation ID:
   ```
   https://teams.microsoft.com/l/channel/19%3A...
   ```
4. The part after `channel/` (URL-decoded) is your conversation ID
5. Add to `.env`: `TEAMS_CONVERSATION_ID=19:xxxxx...`

## Step 5: Test the Integration

1. Make sure your webhook server is running
2. Make sure the bot is added to a Teams channel/chat
3. Send the bot a test message to establish conversation reference
4. Run an MCP tool that requires approval
5. You should receive an adaptive card in Teams with Approve/Reject buttons
6. Click a button - the approval should be processed

## Troubleshooting

### Bot doesn't receive messages

**Check:**
- Messaging endpoint is correct in Azure Bot configuration
- URL is HTTPS (required by Teams)
- Webhook server is running and accessible
- Bot is actually added to the Teams channel/chat
- Check webhook server logs for errors

**Test endpoint:**
```bash
curl https://your-url/api/messages
# Should return 200 OK
```

### "Unauthorized" errors

**Check:**
- `TEAMS_APP_ID` matches the App ID in Azure
- `TEAMS_APP_PASSWORD` is correct (the secret value, not the ID)
- Secret hasn't expired (check Azure Portal → App Registration → Certificates & secrets)
- Webhook server logs for authentication errors

### Adaptive card doesn't update after clicking button

**Check:**
- Bot Framework SDK version is 4.15.0 or higher
- Using `Action.Execute` (not deprecated `Action.Submit`)
- `on_adaptive_card_invoke` handler is implemented
- Check webhook server logs for invoke activity errors

### Can't send proactive messages

**Check:**
- Conversation reference is stored (send bot a message first)
- `TEAMS_SERVICE_URL` is correct for your region
- Bot has necessary permissions in the manifest

**Fix:**
Send the bot a message in the target channel/chat to store the conversation reference.

## Common Issues and Solutions

### Issue: Bot manifest upload fails

**Solution:**
- Verify `manifest.json` has correct JSON syntax
- Check that App ID matches your Azure App Registration
- Ensure icons are correct sizes (192x192 and 32x32)
- Verify the zip contains files at root level, not in a subdirectory

### Issue: Can't add bot to team

**Solution:**
- Check that your Teams admin allows custom app uploads
- Verify bot is enabled for "team" scope in manifest
- Try adding to a personal chat first, then team

### Issue: Approval buttons don't work

**Solution:**
- Verify using `Action.Execute` not `Action.Submit`
- Check that handler returns proper `InvokeResponse`
- Review webhook server logs for errors
- Test with a simple card first

## Security Considerations

1. **Keep App Password Secret**: Never commit to version control
2. **Use HTTPS**: Teams requires HTTPS for messaging endpoints
3. **Verify Tokens**: Bot Framework SDK handles token verification automatically
4. **Limit Permissions**: Only grant necessary scopes in app manifest
5. **Monitor Logs**: Watch for unusual activity or failed auth attempts

## Production Deployment Checklist

- [ ] Deploy webhook server to cloud with HTTPS (Azure App Service, AWS, GCP, etc.)
- [ ] Update Azure Bot messaging endpoint to production URL
- [ ] Set up log monitoring and alerting
- [ ] Configure proper WSGI server (gunicorn, waitress, etc.)
- [ ] Set `SECURITY_MODE=production`
- [ ] Document App Password rotation procedure
- [ ] Test failover scenarios
- [ ] Set up health check monitoring (`/health` endpoint)

## Additional Resources

- [Microsoft Teams Bot Framework](https://learn.microsoft.com/en-us/microsoftteams/platform/bots/what-are-bots)
- [Adaptive Cards](https://adaptivecards.io/)
- [Bot Framework Python SDK](https://github.com/microsoft/botbuilder-python)
- [Teams App Manifest](https://learn.microsoft.com/en-us/microsoftteams/platform/resources/schema/manifest-schema)
- [Adaptive Cards Designer](https://adaptivecards.io/designer/) - Test card designs

## Next Steps

- [General Setup Guide](../README.md)
- [Slack Setup Guide](./SLACK_SETUP.md)
- [Webex Setup Guide](./WEBEX_SETUP.md)
- [Architecture Documentation](./ARCHITECTURE.md)
