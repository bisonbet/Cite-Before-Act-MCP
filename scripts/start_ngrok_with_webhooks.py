#!/usr/bin/env python3
"""Start ngrok and automatically configure webhooks for enabled platforms."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

try:
    from webexteamssdk import WebexTeamsAPI
    from webexteamssdk.exceptions import ApiError
    WEBEX_AVAILABLE = True
except ImportError:
    WEBEX_AVAILABLE = False


def load_env_file(env_path: Path) -> dict:
    """Load environment variables from .env file."""
    env_vars = {}
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip().strip('"').strip("'")
    return env_vars


def get_ngrok_url(max_attempts: int = 30, delay: float = 1.0) -> Optional[str]:
    """Get ngrok public URL from ngrok API."""
    import urllib.request
    
    for attempt in range(max_attempts):
        try:
            with urllib.request.urlopen('http://localhost:4040/api/tunnels', timeout=2) as response:
                data = json.loads(response.read().decode())
                
                # Prefer HTTPS URL
                for tunnel in data.get('tunnels', []):
                    if tunnel.get('proto') == 'https':
                        return tunnel.get('public_url')
                
                # Fallback to HTTP
                for tunnel in data.get('tunnels', []):
                    if tunnel.get('proto') == 'http':
                        return tunnel.get('public_url')
        except Exception:
            pass
        
        time.sleep(delay)
    
    return None


def setup_webex_webhook(ngrok_url: str, bot_token: str) -> bool:
    """Create or update Webex webhook for attachment actions."""
    if not WEBEX_AVAILABLE:
        print("⚠️  webexteamssdk not installed. Skipping Webex webhook setup.")
        print("   Install with: pip install webexteamssdk")
        return False
    
    webhook_url = f"{ngrok_url}/webex/interactive"
    
    try:
        api = WebexTeamsAPI(access_token=bot_token)
        
        # Delete any existing webhooks for attachmentActions
        print("🔍 Checking for existing Webex webhooks...")
        webhooks = api.webhooks.list()
        for wh in webhooks:
            if wh.resource == "attachmentActions" and wh.event == "created":
                print(f"🗑️  Deleting old webhook: {wh.id}")
                try:
                    api.webhooks.delete(wh.id)
                except Exception:
                    pass
        
        # Create new webhook
        print(f"📝 Creating Webex webhook: {webhook_url}")
        webhook = api.webhooks.create(
            name="Cite-Before-Act Approval Webhook",
            targetUrl=webhook_url,
            resource="attachmentActions",
            event="created"
        )
        
        print(f"✅ Webex webhook created successfully!")
        print(f"   ID: {webhook.id}")
        print(f"   URL: {webhook.targetUrl}")
        print(f"   Status: {webhook.status}")
        return True
        
    except ApiError as e:
        print(f"❌ Failed to create Webex webhook: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"❌ Error setting up Webex webhook: {e}", file=sys.stderr)
        return False


def setup_teams_webhook(ngrok_url: str) -> None:
    """Print instructions for Teams webhook setup."""
    messaging_endpoint = f"{ngrok_url}/api/messages"
    print("\n📋 Teams Webhook Setup (Manual):")
    print(f"   Messaging Endpoint: {messaging_endpoint}")
    print("   1. Go to Azure Portal → Your Bot → Configuration")
    print("   2. Set Messaging endpoint to the URL above")
    print("   3. Click Apply")


def main():
    """Main function."""
    # Get project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    env_file = project_root / ".env"
    
    # Load .env file
    env_vars = load_env_file(env_file)
    for key, value in env_vars.items():
        os.environ.setdefault(key, value)
    
    # Get configuration
    port = int(os.getenv("PORT", "3000"))
    enable_webex = os.getenv("ENABLE_WEBEX", "false").lower() == "true"
    enable_teams = os.getenv("ENABLE_TEAMS", "false").lower() == "true"
    enable_slack = os.getenv("ENABLE_SLACK", "false").lower() == "true"
    webex_token = os.getenv("WEBEX_BOT_TOKEN")
    
    # Check if ngrok is installed
    try:
        subprocess.run(["ngrok", "version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Error: ngrok is not installed")
        print("   Install from: https://ngrok.com/download")
        sys.exit(1)
    
    # Start ngrok
    print(f"🚀 Starting ngrok on port {port}...")
    ngrok_process = subprocess.Popen(
        ["ngrok", "http", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    try:
        # Wait for ngrok to start
        time.sleep(2)
        
        # Get ngrok URL
        print("⏳ Waiting for ngrok URL...")
        ngrok_url = get_ngrok_url()
        
        if not ngrok_url:
            print("❌ Error: Could not get ngrok URL")
            print("   Make sure ngrok is running and accessible at http://localhost:4040")
            ngrok_process.terminate()
            sys.exit(1)
        
        print(f"✅ ngrok is running")
        print(f"   URL: {ngrok_url}")
        print()
        
        # Setup webhooks
        if enable_webex and webex_token:
            setup_webex_webhook(ngrok_url, webex_token)
        elif enable_webex:
            print("⚠️  ENABLE_WEBEX=true but WEBEX_BOT_TOKEN not set")
        
        if enable_teams:
            setup_teams_webhook(ngrok_url)
        
        # Print summary
        print("\n" + "=" * 70)
        print("✅ ngrok is ready!")
        print("=" * 70)
        print("\n📝 Webhook URLs:")
        if enable_slack:
            print(f"   Slack:  {ngrok_url}/slack/interactive")
        if enable_webex:
            print(f"   Webex:  {ngrok_url}/webex/interactive")
        if enable_teams:
            print(f"   Teams:  {ngrok_url}/api/messages")
        print("\n" + "=" * 70)
        print("Press Ctrl+C to stop ngrok")
        print("=" * 70)
        
        # Wait for ngrok process
        try:
            ngrok_process.wait()
        except KeyboardInterrupt:
            print("\n\n🛑 Stopping ngrok...")
            ngrok_process.terminate()
            ngrok_process.wait()
            print("✅ ngrok stopped")
    
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        ngrok_process.terminate()
        sys.exit(1)


if __name__ == "__main__":
    main()

