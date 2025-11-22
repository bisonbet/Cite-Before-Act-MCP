#!/usr/bin/env python3
"""Check and create Webex webhook for attachment actions."""

import os
import sys
from webexteamssdk import WebexTeamsAPI
from webexteamssdk.exceptions import ApiError

def main():
    """Check existing webhooks and optionally create a new one."""
    # Get bot token from environment
    bot_token = os.getenv("WEBEX_BOT_TOKEN")
    if not bot_token:
        print("Error: WEBEX_BOT_TOKEN environment variable not set", file=sys.stderr)
        sys.exit(1)

    # Get webhook URL from environment or prompt
    webhook_url = os.getenv("WEBEX_WEBHOOK_URL")
    if not webhook_url:
        webhook_url = input("Enter your webhook URL (e.g., https://abc123.ngrok.io/webex/interactive): ").strip()
        if not webhook_url:
            print("Error: Webhook URL is required", file=sys.stderr)
            sys.exit(1)

    # Ensure URL ends with /webex/interactive
    if not webhook_url.endswith("/webex/interactive"):
        if webhook_url.endswith("/"):
            webhook_url = webhook_url + "webex/interactive"
        else:
            webhook_url = webhook_url + "/webex/interactive"

    api = WebexTeamsAPI(access_token=bot_token)

    print("Checking existing webhooks...")
    print(f"Looking for webhook pointing to: {webhook_url}")
    print()

    # List all webhooks
    try:
        webhooks = api.webhooks.list()
        existing_webhook = None
        
        for wh in webhooks:
            print(f"Webhook ID: {wh.id}")
            print(f"  Name: {wh.name}")
            print(f"  URL: {wh.targetUrl}")
            print(f"  Resource: {wh.resource}")
            print(f"  Event: {wh.event}")
            print(f"  Status: {wh.status}")
            print()
            
            # Check if this is our webhook
            if (wh.resource == "attachmentActions" and 
                wh.event == "created" and 
                wh.targetUrl == webhook_url):
                existing_webhook = wh
                print(f"✅ Found matching webhook: {wh.id}")
                print()

        # Check if we need to create a new webhook
        if not existing_webhook:
            print("❌ No webhook found for attachmentActions -> created")
            print()
            create = input("Create a new webhook? (y/n): ").strip().lower()
            
            if create == 'y':
                try:
                    new_webhook = api.webhooks.create(
                        name="Cite-Before-Act Approval Webhook",
                        targetUrl=webhook_url,
                        resource="attachmentActions",
                        event="created"
                    )
                    print(f"✅ Created webhook: {new_webhook.id}")
                    print(f"   URL: {new_webhook.targetUrl}")
                    print(f"   Status: {new_webhook.status}")
                except ApiError as e:
                    print(f"❌ Failed to create webhook: {e}", file=sys.stderr)
                    sys.exit(1)
            else:
                print("Webhook not created. Exiting.")
        else:
            # Check status
            if existing_webhook.status != "active":
                print(f"⚠️  Webhook exists but status is '{existing_webhook.status}'")
                print("   This usually means Webex can't reach your server.")
                print("   Check that:")
                print("   1. Your webhook server is running")
                print("   2. ngrok is running and URL is correct")
                print("   3. The endpoint /webex/interactive is accessible")
            else:
                print("✅ Webhook is active and ready!")
                print()
                print("To test:")
                print("1. Make sure your webhook server is running")
                print("2. Make sure ngrok is running")
                print("3. Click a button on an approval card in Webex")
                print("4. Check webhook server logs for incoming requests")

    except ApiError as e:
        print(f"❌ Webex API error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

