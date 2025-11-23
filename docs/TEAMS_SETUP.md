# Microsoft Teams Bot Setup Guide

This guide will walk you through setting up a Microsoft Teams bot for approval notifications with Cite-Before-Act MCP.

## ⚠️ IMPORTANT: Account Requirements

**This integration REQUIRES a Microsoft Teams work or school account. Personal Microsoft accounts (@outlook.com, @hotmail.com) are NOT supported.**

To use this Teams bot integration, you must have:
- A **work or school Microsoft Teams account** (organizational account)
- An Azure subscription with permissions to create App Registrations and Bot Services
- Your organization must allow custom app uploads in Teams

**Personal Microsoft accounts cannot create Azure Bot Services or upload custom apps to Teams.** If you only have a personal account, you will need to use Slack or Webex instead.

## Prerequisites

- **Microsoft Teams work or school account** (organizational account) - **MANDATORY**
- Azure account with permissions to create App Registrations and Bot Services
- Microsoft Teams workspace where you can add bots
- Public HTTPS endpoint (use ngrok for development, or deploy to cloud)
- Python 3.10+ (required for botbuilder-core 4.15.0+)
- Required Python packages: `botbuilder-core`, `botframework-connector`, and `aiohttp`

## Architecture Overview

Unlike Slack and Webex which use simple webhooks, Microsoft Teams requires:
1. **Azure Bot Service** - Manages bot authentication and message routing
2. **App Registration** - Provides App ID and Password for authentication (created in Microsoft Entra ID)
3. **Messaging Endpoint** - Public HTTPS URL where your bot receives messages
4. **Bot Framework SDK** - Handles bot protocol and adaptive cards

**Important**: Despite being more complex, Teams bots work via webhooks just like Slack/Webex - they don't maintain persistent connections. Teams sends HTTP POST requests to your bot's endpoint.

**Note on Bot Types**: Microsoft has announced that multi-tenant bot creation will be deprecated after July 31, 2025. For new bots, consider using **single-tenant** or **user-assigned managed identity** bot types. Existing multi-tenant bots will continue to function after the deprecation date.

**Note on Account Types**: This integration requires a work or school Teams account. While Azure App Registration technically supports personal Microsoft accounts in the account type selection, **personal Teams accounts cannot use custom bots** due to Teams policy restrictions. You must use a work or school account to upload and use custom Teams apps.

## Step 1: Create Azure Bot Registration

**Note**: Microsoft has rebranded "Azure Active Directory" to "Microsoft Entra ID". All references in this guide use the current terminology.

### 1.1 Register an Application in Microsoft Entra ID

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Microsoft Entra ID** → **App registrations**
   - **Note**: Microsoft Entra ID is the new name for Azure Active Directory (Azure AD)
3. Click **New registration**
   - Name: `Cite-Before-Act Approval Bot`
   - Supported account types: Choose based on your needs:
     - **For organizational accounts only** (recommended):
       - Select: `Accounts in any organizational directory (Any Microsoft Entra directory - Multitenant)`
       - **Note**: Multi-tenant bot creation will be deprecated after July 31, 2025. For new bots, consider using **Single tenant** instead.
     - **For single organization only**:
       - Select: `Accounts in this organizational directory only (Single tenant)`
     - **⚠️ Important**: Do NOT select the option that includes "personal Microsoft accounts" - personal Teams accounts cannot use custom bots. This integration requires a work or school account.
   - Redirect URI: Leave blank for now
4. Click **Register**

### 1.2 Get App Credentials

1. **Get Application (client) ID and Directory (tenant) ID**:
   - In your app registration, go to the **Overview** page (should be the default page)
   - Copy the **Application (client) ID** - This is your `TEAMS_APP_ID`
   - Copy the **Directory (tenant) ID** - This is your `TEAMS_TENANT_ID` (optional but recommended)
   - **Note**: The Directory (tenant) ID is also called "App tenant ID" or "Tenant ID"

2. **Generate Client Secret**:
   - Go to **Certificates & secrets** in the left menu
   - Click **New client secret**
     - Description: `Bot password`
     - Expires: Choose your preferred expiration (recommend 12-24 months)
   - Click **Add**
   - **CRITICAL**: Copy the **Value** immediately - you won't be able to see it again!
     - This is your `TEAMS_APP_PASSWORD`

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

1. Go to your Azure Bot resource in Azure Portal
2. In the left menu, click **Configuration** (or **Settings** → **Configuration** in some Azure Portal versions)
3. Find the **Messaging endpoint** field
4. Set the endpoint URL:
   - For development: `https://your-ngrok-url.ngrok.io/api/messages`
   - For production: `https://your-domain.com/api/messages`
   - **Important**: Must be HTTPS (Teams requires secure connections)
5. **Enable streaming endpoint**: Leave this **unchecked/disabled**
   - Streaming endpoints are only needed for real-time audio/video streaming
   - This approval bot only handles text messages and adaptive cards, so streaming is not required
6. Click **Apply** or **Save** to save the configuration

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

**manifest.json** (replace `YOUR_APP_ID` with your actual App ID from Step 1.2):

**Note**: This example uses manifest version 1.19 (September 2024). You can use a newer version if available. See the [Teams App Manifest Schema documentation](https://learn.microsoft.com/en-us/microsoftteams/platform/resources/schema/manifest-schema) for the latest version.

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/teams/v1.19/MicrosoftTeams.schema.json",
  "manifestVersion": "1.19",
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
2. Access the Apps section using one of these methods:
   - **Method 1**: Click **Apps** in the left sidebar (if visible)
   - **Method 2**: Click the **three dots (⋯)** or **More options** menu at the bottom of the left sidebar, then select **Apps**
   - **Method 3**: Use the search bar at the top and search for "Apps"
   - **Method 4**: In some Teams versions, click **Built by your org** or **More apps** at the bottom left
3. Once in the Apps view, look for **Upload a custom app** or **Manage your apps**:
   - This may be at the bottom left of the Apps page
   - Or click the **three dots (⋯)** menu in the Apps view and select **Upload a custom app**
   - Some versions show **"Built by your org"** → **"Upload a custom app"**
4. Click **Upload a custom app** (or **Upload an app** → **Upload a custom app**)
5. Select your `teams-app-manifest.zip` file
6. Click **Add** to add the bot to a team/chat

**Note**: The exact location of the upload option varies by Teams version and organization settings. If you don't see these options, your organization may have restricted custom app uploads. Contact your Teams administrator if needed.

## Step 3: Configure Cite-Before-Act MCP

### 3.1 Set Environment Variables

Add to your `.env` file:

```bash
# Enable Microsoft Teams
ENABLE_TEAMS=true

# Teams Bot Credentials
TEAMS_APP_ID=your-app-id-from-step-1.2
TEAMS_APP_PASSWORD=your-app-password-from-step-1.2

# Tenant ID (REQUIRED for single-tenant apps, HIGHLY RECOMMENDED for multi-tenant)
# Found on Overview page as "Directory (tenant) ID"
# Without this, you may get "AADSTS700016: Application not found in directory 'Bot Framework'" errors
TEAMS_TENANT_ID=your-tenant-id-from-step-1.2

# Optional: Service URL (usually default is fine)
TEAMS_SERVICE_URL=https://smba.trafficmanager.net/amer/

# Optional: Pre-configure conversation (will auto-detect otherwise)
# TEAMS_CONVERSATION_ID=your-channel-or-chat-id
```

### 3.2 Install Dependencies

Install the required Bot Framework packages and dependencies:

```bash
pip install botbuilder-core>=4.15.0 botframework-connector>=4.15.0 aiohttp
```

Or install all dependencies from requirements.txt:

```bash
pip install -r requirements.txt
```

**Note**: Ensure you're using Python 3.10 or higher, as botbuilder-core 4.15.0+ requires Python 3.10+.

**Required packages:**
- `botbuilder-core>=4.15.0` - Bot Framework core functionality
- `botframework-connector>=4.15.0` - Bot Framework connector for Teams
- `aiohttp` - Async HTTP client/server library (required by Bot Framework)

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

The bot needs to know where to send approval requests. The conversation reference is captured when the bot receives messages or is added to a conversation.

**Important**: The unified webhook server (`unified_webhook_server.py`) currently logs conversation references but doesn't persist them automatically. For production use, you'll need to either:
- Store conversation references in a file/database and load them when sending approvals
- Use the conversation reference from each incoming message
- Pre-configure the conversation ID (see Step 4.2)

### 4.1 Establish Conversation Reference (Recommended for Testing)

1. Open Teams and go to the chat/channel where you added the bot
2. Send a message to the bot (e.g., "hello")
3. The bot will receive the message and log the conversation reference
4. Check the webhook server logs - you should see activity indicating the message was received
5. **Note**: The conversation reference is available in the activity but needs to be stored if you want to send proactive messages later

### 4.2 Find Conversation ID Manually (Recommended for Production)

If you want to pre-configure the conversation ID to avoid needing to store references dynamically:

1. Open Teams in a web browser
2. Navigate to your team/channel where the bot is installed
3. Look at the URL - it contains the conversation ID:
   ```
   https://teams.microsoft.com/l/channel/19%3A...
   ```
4. The part after `channel/` (URL-encoded) needs to be decoded:
   - `19%3A` decodes to `19:`
   - The full conversation ID format is: `19:xxxxx...`
5. Copy the full conversation ID (everything after `/channel/`, URL-decoded)
6. Add to your `.env` file:
   ```bash
   TEAMS_CONVERSATION_ID=19:xxxxx...
   ```
7. If you haven't already added it, add your tenant ID (found in Step 1.2 on the Overview page as "Directory (tenant) ID"):
   ```bash
   TEAMS_TENANT_ID=your-tenant-id-from-step-1.2
   ```

**Alternative**: Extract from webhook server logs when the bot receives a message - the conversation ID will be in the activity JSON.

## Step 5: Test the Integration

1. **Start the webhook server** (see Step 3.3)
2. **Verify the bot is added** to a Teams channel/chat (see Step 2.3)
3. **Establish conversation reference**:
   - Send the bot a test message (e.g., "hello") in Teams
   - Check webhook server logs to confirm message was received
   - If using pre-configured conversation ID, skip this step
4. **Trigger an approval request**:
   - Run an MCP tool that requires approval (e.g., `write_file`, `create_repository`)
   - The Cite-Before-Act middleware should detect it as mutating
5. **Check Teams for approval card**:
   - You should receive an adaptive card in Teams with Approve/Reject buttons
   - The card shows the tool name, description, and arguments
6. **Test approval/rejection**:
   - Click **Approve** or **Reject** button
   - The card should update to show the status
   - Check webhook server logs for approval response
   - The MCP tool should proceed (if approved) or be rejected (if rejected)

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
# Test that endpoint is accessible (may return 400 without proper auth, which is OK)
curl -X POST https://your-url/api/messages \
  -H "Content-Type: application/json" \
  -d '{"type":"message"}'
# Should return 200 OK or 400 Bad Request (both indicate endpoint is working)
```

**Note**: A 400 response is normal without proper Bot Framework authentication headers. A 404 means the endpoint isn't configured correctly.

### "Unauthorized" errors

**Check:**
- `TEAMS_APP_ID` matches the App ID in Azure
- `TEAMS_APP_PASSWORD` is correct (the secret value, not the ID)
- Secret hasn't expired (check Azure Portal → Microsoft Entra ID → App registrations → Your app → Certificates & secrets)
- Webhook server logs for authentication errors

### "AADSTS700016: Application not found in directory 'Bot Framework'" error

**Symptoms:**
- Error message: `AADSTS700016: Application with identifier '...' was not found in the directory 'Bot Framework'`
- Authentication fails when trying to send messages or get access tokens

**Cause:**
The Bot Framework adapter is trying to authenticate against the "Bot Framework" tenant instead of your Azure AD tenant. This happens when the tenant ID is not configured.

**Solution:**
1. **Set the Tenant ID** in your `.env` file:
   ```bash
   TEAMS_TENANT_ID=your-tenant-id-here
   ```
   You can find your tenant ID in Azure Portal → Microsoft Entra ID → App registrations → Your app → Overview page (listed as "Directory (tenant) ID")

2. **Verify the tenant ID is correct**:
   - Go to Azure Portal → Microsoft Entra ID → Overview
   - Copy the "Tenant ID" value
   - Ensure it matches the tenant where your app is registered

3. **Restart your webhook server** after setting `TEAMS_TENANT_ID`

4. **For single-tenant apps**: If your app registration is configured as "Single tenant", the tenant ID is **required**. For multi-tenant apps, it's still recommended to set it to avoid authentication issues.

**Note**: The tenant ID is now automatically used to configure tenant-specific authentication, ensuring all token requests go to the correct Azure AD tenant instead of the non-existent "Bot Framework" tenant.

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

### Issue: Can't find "Apps" in Teams sidebar

**Symptoms:**
- "Apps" option is not visible in the left sidebar
- Can't find where to upload custom apps

**Solutions:**
1. **Check Teams version**: Update Microsoft Teams to the latest version
2. **Try alternative access methods**:
   - Click the **three dots (⋯)** or **More options** menu at the bottom of the left sidebar
   - Look for **"Built by your org"** or **"More apps"** at the bottom left
   - Use the search bar at the top and search for "Apps"
3. **Check organization policies**: Your organization may have restricted custom app uploads
   - Contact your Teams administrator to enable custom app uploads
   - Some organizations require admin approval for custom apps
4. **Try Teams web version**: Sometimes the web version (teams.microsoft.com) has different UI
5. **Check account type**: Personal Microsoft accounts may have limited app management features
   - Organizational accounts typically have full access to app management

**Alternative**: If you have admin access, you can also upload apps via the [Teams Admin Center](https://admin.teams.microsoft.com/) under **Teams apps** → **Manage apps**.

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
- Verify using `Action.Execute` (not deprecated `Action.Submit`) in adaptive card
- Check that `on_adaptive_card_invoke` handler is implemented correctly
- Verify handler returns proper `InvokeResponse` with status 200
- Check webhook server logs for invoke activity errors
- Ensure Bot Framework SDK version is 4.15.0 or higher
- Test with a simple card first to isolate the issue

### Issue: Conversation reference not stored

**Solution:**
- The unified webhook server logs conversation references but doesn't persist them by default
- For production, implement conversation reference storage (file/database)
- Alternatively, pre-configure `TEAMS_CONVERSATION_ID` in `.env` file
- Check webhook server logs when bot receives messages to extract conversation ID

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

- [Microsoft Teams Bot Framework Documentation](https://learn.microsoft.com/en-us/microsoftteams/platform/bots/what-are-bots)
- [Azure Bot Service Documentation](https://learn.microsoft.com/en-us/azure/bot-service/bot-service-overview-introduction)
- [Microsoft Entra ID Documentation](https://learn.microsoft.com/en-us/entra/)
- [Bot Framework Python SDK](https://github.com/microsoft/botbuilder-python)
- [Bot Framework Python Samples](https://github.com/microsoft/botbuilder-python/tree/main/samples)
- [Teams App Manifest Schema](https://learn.microsoft.com/en-us/microsoftteams/platform/resources/schema/manifest-schema)
- [Adaptive Cards Documentation](https://adaptivecards.io/)
- [Adaptive Cards Designer](https://adaptivecards.io/designer/) - Test card designs
- [Bot Framework Authentication](https://learn.microsoft.com/en-us/azure/bot-service/bot-builder-authentication)
- [Bot Identity Types (Multi-tenant deprecation notice)](https://learn.microsoft.com/en-us/azure/bot-service/bot-service-manage-settings?view=azure-bot-service-4.0&tabs=userassigned#configuration)

## Next Steps

- [General Setup Guide](../README.md)
- [Slack Setup Guide](./SLACK_SETUP.md)
- [Webex Setup Guide](./WEBEX_SETUP.md)
- [Architecture Documentation](./ARCHITECTURE.md)
