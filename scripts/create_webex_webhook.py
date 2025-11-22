#!/usr/bin/env python3
"""Quick script to create a Webex webhook for attachment actions."""

import os
import sys
from webexteamssdk import WebexTeamsAPI

# Get values from environment or command line
bot_token = os.getenv("WEBEX_BOT_TOKEN")
webhook_url = sys.argv[1] if len(sys.argv) > 1 else os.getenv("WEBEX_WEBHOOK_URL")

if not bot_token:
    print("Error: Set WEBEX_BOT_TOKEN environment variable", file=sys.stderr)
    sys.exit(1)

if not webhook_url:
    print("Usage: python create_webex_webhook.py <webhook-url>", file=sys.stderr)
    print("   or: export WEBEX_WEBHOOK_URL=... && python create_webex_webhook.py", file=sys.stderr)
    sys.exit(1)

# Ensure URL ends with /webex/interactive
if not webhook_url.endswith("/webex/interactive"):
    webhook_url = webhook_url.rstrip("/") + "/webex/interactive"

api = WebexTeamsAPI(access_token=bot_token)

print(f"Creating webhook for: {webhook_url}")

try:
    # Delete any existing webhooks for attachmentActions first
    print("Checking for existing webhooks...")
    webhooks = api.webhooks.list()
    for wh in webhooks:
        if wh.resource == "attachmentActions" and wh.event == "created":
            print(f"Deleting existing webhook: {wh.id}")
            api.webhooks.delete(wh.id)

    # Create new webhook
    webhook = api.webhooks.create(
        name="Cite-Before-Act Approval Webhook",
        targetUrl=webhook_url,
        resource="attachmentActions",
        event="created"
    )
    
    print(f"✅ Webhook created successfully!")
    print(f"   ID: {webhook.id}")
    print(f"   URL: {webhook.targetUrl}")
    print(f"   Status: {webhook.status}")
    print()
    print("Now test by clicking a button on an approval card in Webex.")
    
except Exception as e:
    print(f"❌ Error: {e}", file=sys.stderr)
    sys.exit(1)

