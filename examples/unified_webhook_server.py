"""Unified Webhook Server for Slack, Webex, and Microsoft Teams approval responses.

A production-ready Flask webhook server that receives interactive button clicks
for approval/rejection from Slack, Webex Teams, and Microsoft Teams.

The webhook must be publicly accessible (use ngrok or deploy to cloud/VPS).

Security Modes:
    - LOCAL (default): For web service hosted (ngrok with traffic policy)
        * Validates approval_id format (prevents path traversal)
        * Optional debug mode
        * No application-level HMAC verification (ngrok handles it)
        * Use with: ngrok traffic policy for signature verification

    - PRODUCTION: For self-hosted (direct internet exposure)
        * Platform signature verification (Slack HMAC, Teams JWT)
        * Approval_id validation (prevents path traversal)
        * Configurable rate limiting
        * Input validation
        * Sanitized error messages

Environment Variables:
    # Common
    SECURITY_MODE=local|production  # Default: local
    PORT=3000                       # Default: 3000
    DEBUG=false                     # Default: false

    # Slack (optional - only if using Slack)
    ENABLE_SLACK=true              # Default: false
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_SIGNING_SECRET=...       # Required for production mode

    # Webex (optional - only if using Webex)
    ENABLE_WEBEX=true              # Default: false
    WEBEX_BOT_TOKEN=...

    # Teams (optional - only if using Teams)
    ENABLE_TEAMS=true              # Default: false
    TEAMS_APP_ID=...
    TEAMS_APP_PASSWORD=...

Usage:
    1. Install dependencies:
       pip install flask slack-sdk webexteamssdk botbuilder-core botframework-connector

    2. Enable platforms:
       export ENABLE_SLACK=true
       export ENABLE_WEBEX=true
       export ENABLE_TEAMS=true

    3. Set credentials for enabled platforms (see above)

    4. Run server:
       python examples/unified_webhook_server.py

    5. Configure webhooks in each platform:
       - Slack: https://your-url/slack/interactive
       - Webex: https://your-url/webex/interactive
       - Teams: https://your-url/api/messages

See documentation for detailed setup instructions.
"""

import asyncio
import hashlib
import hmac
import json
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

app = Flask(__name__)

# Configuration
SECURITY_MODE = os.getenv("SECURITY_MODE", "local").lower()
PORT = int(os.getenv("PORT", 3000))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
HOST = os.getenv("HOST", "127.0.0.1" if SECURITY_MODE == "local" else "0.0.0.0")

# Platform enablement
ENABLE_SLACK = os.getenv("ENABLE_SLACK", "false").lower() == "true"
ENABLE_WEBEX = os.getenv("ENABLE_WEBEX", "false").lower() == "true"
ENABLE_TEAMS = os.getenv("ENABLE_TEAMS", "false").lower() == "true"

# Rate limiting (production mode only)
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", 60))
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", 60))

# Validate base configuration
if SECURITY_MODE not in ["local", "production"]:
    print(f"Error: SECURITY_MODE must be 'local' or 'production', got: {SECURITY_MODE}", file=sys.stderr)
    sys.exit(1)

if not any([ENABLE_SLACK, ENABLE_WEBEX, ENABLE_TEAMS]):
    print("Error: At least one platform must be enabled (ENABLE_SLACK, ENABLE_WEBEX, or ENABLE_TEAMS)", file=sys.stderr)
    sys.exit(1)

# Initialize platform clients
slack_handler = None
webex_handler = None
teams_handler = None
teams_adapter = None
teams_client = None

# Slack setup
if ENABLE_SLACK:
    try:
        from slack_sdk import WebClient
        from cite_before_act.slack.handlers import SlackHandler

        SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
        SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")

        if not SLACK_BOT_TOKEN:
            print("Error: SLACK_BOT_TOKEN required when ENABLE_SLACK=true", file=sys.stderr)
            sys.exit(1)

        if SECURITY_MODE == "production" and not SLACK_SIGNING_SECRET:
            print("Error: SLACK_SIGNING_SECRET required for Slack in production mode", file=sys.stderr)
            sys.exit(1)

        slack_client = WebClient(token=SLACK_BOT_TOKEN)
        slack_handler = SlackHandler(client=slack_client)
        print("✅ Slack handler initialized", file=sys.stderr)
    except ImportError as e:
        print(f"Error: Failed to import Slack dependencies: {e}", file=sys.stderr)
        print("Install with: pip install slack-sdk", file=sys.stderr)
        sys.exit(1)

# Webex setup
if ENABLE_WEBEX:
    try:
        from cite_before_act.webex.handlers import WebexHandler

        WEBEX_BOT_TOKEN = os.getenv("WEBEX_BOT_TOKEN")

        if not WEBEX_BOT_TOKEN:
            print("Error: WEBEX_BOT_TOKEN required when ENABLE_WEBEX=true", file=sys.stderr)
            sys.exit(1)

        webex_handler = WebexHandler(access_token=WEBEX_BOT_TOKEN)
        print("✅ Webex handler initialized", file=sys.stderr)
    except ImportError as e:
        print(f"Error: Failed to import Webex dependencies: {e}", file=sys.stderr)
        print("Install with: pip install webexteamssdk", file=sys.stderr)
        sys.exit(1)

# Teams setup
if ENABLE_TEAMS:
    try:
        from cite_before_act.teams import create_teams_adapter, parse_teams_activity, TeamsHandler, TeamsClient

        TEAMS_APP_ID = os.getenv("TEAMS_APP_ID")
        TEAMS_APP_PASSWORD = os.getenv("TEAMS_APP_PASSWORD")
        TEAMS_TENANT_ID = os.getenv("TEAMS_TENANT_ID")
        TEAMS_SERVICE_URL = os.getenv("TEAMS_SERVICE_URL", "https://smba.trafficmanager.net/amer/")

        if not TEAMS_APP_ID or not TEAMS_APP_PASSWORD:
            print("Error: TEAMS_APP_ID and TEAMS_APP_PASSWORD required when ENABLE_TEAMS=true", file=sys.stderr)
            sys.exit(1)

        teams_adapter = create_teams_adapter(
            TEAMS_APP_ID,
            TEAMS_APP_PASSWORD,
            tenant_id=TEAMS_TENANT_ID,
        )

        # Create Teams client for sending proactive messages
        teams_client = TeamsClient(
            adapter=teams_adapter,
            service_url=TEAMS_SERVICE_URL,
            tenant_id=TEAMS_TENANT_ID,
        )

        # Create Teams handler and wire it to save conversation references to the client and file
        def save_conversation_reference(turn_context):
            """Callback to save conversation reference when bot receives messages."""
            # Save to client (for webhook server to send messages)
            teams_client.set_conversation_reference(turn_context)

            # Also save to file so MCP server can load it and send approval requests
            try:
                from botbuilder.core import TurnContext
                conv_ref = TurnContext.get_conversation_reference(turn_context.activity)
                conv_ref_file = "/tmp/cite-before-act-teams-conversation-reference.json"

                # Extract conversation ID - remove message ID suffix if present
                conversation_id = conv_ref.conversation.id
                if ';messageid=' in conversation_id:
                    conversation_id = conversation_id.split(';messageid=')[0]

                with open(conv_ref_file, "w") as f:
                    json.dump({
                        "service_url": conv_ref.service_url,
                        "channel_id": conv_ref.channel_id,
                        "conversation_id": conversation_id,
                        "tenant_id": conv_ref.conversation.tenant_id if conv_ref.conversation else None,
                    }, f)
                print(
                    f"📝 Saved Teams conversation reference to file: {conversation_id}",
                    file=sys.stderr,
                )
            except Exception as e:
                print(f"⚠️ Error saving Teams conversation reference to file: {e}", file=sys.stderr)

        teams_handler = TeamsHandler(on_conversation_reference=save_conversation_reference)
        print("✅ Teams handler and client initialized", file=sys.stderr)
    except ImportError as e:
        print(f"Error: Failed to import Teams dependencies: {e}", file=sys.stderr)
        print("Install with: pip install botbuilder-core botframework-connector", file=sys.stderr)
        sys.exit(1)

# Rate limiting store
if SECURITY_MODE == "production":
    _rate_limit_store = defaultdict(list)


def validate_approval_id(approval_id: str) -> bool:
    """Validate approval_id format to prevent path traversal attacks."""
    if not re.match(r'^[a-zA-Z0-9_-]+$', approval_id):
        return False
    if len(approval_id) > 100:
        return False
    return True


def verify_slack_signature(request_body: bytes, timestamp: str, signature: str) -> bool:
    """Verify Slack request signature using HMAC-SHA256."""
    if not SLACK_SIGNING_SECRET:
        return False

    try:
        request_timestamp = int(timestamp)
        if abs(time.time() - request_timestamp) > 60 * 5:
            print("Warning: Slack request timestamp too old", file=sys.stderr)
            return False
    except (ValueError, TypeError):
        return False

    sig_basestring = f"v0:{timestamp}:{request_body.decode('utf-8')}"
    expected_signature = 'v0=' + hmac.new(
        SLACK_SIGNING_SECRET.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature)


def check_rate_limit(client_id: str) -> bool:
    """Check if client has exceeded rate limit."""
    if SECURITY_MODE != "production":
        return True

    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW

    _rate_limit_store[client_id] = [
        ts for ts in _rate_limit_store[client_id]
        if ts > window_start
    ]

    if len(_rate_limit_store[client_id]) >= RATE_LIMIT_MAX_REQUESTS:
        return False

    _rate_limit_store[client_id].append(now)
    return True


def validate_payload_size(payload: str) -> bool:
    """Validate payload size to prevent memory exhaustion."""
    MAX_PAYLOAD_SIZE = 100 * 1024  # 100KB
    return len(payload) <= MAX_PAYLOAD_SIZE


def write_approval_response(approval_id: str, approved: bool, platform: str) -> None:
    """Write approval response to a file that the MCP server can read."""
    approval_file = f"/tmp/cite-before-act-{platform}-approval-{approval_id}.json"
    try:
        with open(approval_file, "w") as f:
            json.dump({
                "approval_id": approval_id,
                "approved": approved,
                "platform": platform,
                "timestamp": time.time(),
            }, f)
        print(f"Wrote {platform} approval: {approval_id} -> {approved}", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"Error writing {platform} approval file: {e}", file=sys.stderr, flush=True)


# Slack endpoint
@app.route("/slack/interactive", methods=["POST"])
def slack_interactive():
    """Handle Slack interactive component events."""
    if not ENABLE_SLACK:
        return jsonify({"error": "Slack not enabled"}), 404

    # Verify signature in production
    if SECURITY_MODE == "production":
        timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
        signature = request.headers.get("X-Slack-Signature", "")

        if not verify_slack_signature(request.get_data(), timestamp, signature):
            print("Warning: Invalid Slack signature", file=sys.stderr)
            return jsonify({"error": "Invalid signature"}), 401

    # Rate limiting
    if SECURITY_MODE == "production":
        if not check_rate_limit(request.remote_addr or "unknown"):
            return jsonify({"error": "Rate limit exceeded"}), 429

    # Get payload
    payload = request.form.get("payload")
    if not payload or not validate_payload_size(payload):
        return jsonify({"error": "Invalid payload"}), 400

    try:
        payload_dict = json.loads(payload) if isinstance(payload, str) else payload
        response = slack_handler.handle_interaction(payload_dict)

        # Write approval response
        for action in payload_dict.get("actions", []):
            if action.get("action_id") in ("approve_action", "reject_action"):
                value_data = json.loads(action["value"]) if isinstance(action["value"], str) else action["value"]
                approval_id = value_data.get("approval_id")

                if approval_id and validate_approval_id(approval_id):
                    approved = action["action_id"] == "approve_action"
                    write_approval_response(approval_id, approved, "slack")

        return jsonify(response)
    except Exception as e:
        error_msg = "Internal error" if SECURITY_MODE == "production" else str(e)
        print(f"Slack error: {e}", file=sys.stderr)
        return jsonify({"error": error_msg}), 500


# Webex endpoint
@app.route("/webex/interactive", methods=["POST"])
def webex_interactive():
    """Handle Webex attachment action webhooks."""
    if not ENABLE_WEBEX:
        return jsonify({"error": "Webex not enabled"}), 404

    # Rate limiting
    if SECURITY_MODE == "production":
        if not check_rate_limit(request.remote_addr or "unknown"):
            return jsonify({"error": "Rate limit exceeded"}), 429

    try:
        webhook_data = request.json
        if not webhook_data:
            return jsonify({"error": "No webhook data"}), 400

        # Handle the attachment action
        response = webex_handler.handle_attachment_action(webhook_data)

        # Write approval response if successful
        if response.get("status") == "success":
            approval_id = response.get("approval_id")
            approved = response.get("approved")

            if approval_id and validate_approval_id(approval_id):
                write_approval_response(approval_id, approved, "webex")

        return jsonify(response)
    except Exception as e:
        error_msg = "Internal error" if SECURITY_MODE == "production" else str(e)
        print(f"Webex error: {e}", file=sys.stderr)
        return jsonify({"error": error_msg}), 500


# Teams endpoint
@app.route("/api/messages", methods=["POST"])
def teams_messages():
    """Handle Microsoft Teams bot messages and invoke activities."""
    if not ENABLE_TEAMS:
        return jsonify({"error": "Teams not enabled"}), 404

    # Rate limiting
    if SECURITY_MODE == "production":
        if not check_rate_limit(request.remote_addr or "unknown"):
            return jsonify({"error": "Rate limit exceeded"}), 429

    try:
        body = request.json
        if not body:
            return jsonify({"error": "No request body"}), 400

        # Parse activity
        activity = parse_teams_activity(body)
        auth_header = request.headers.get("Authorization", "")

        # Process the activity
        async def process_activity(turn_context):
            await teams_handler.on_turn(turn_context)

        # Run async processing
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                teams_adapter.process_activity(activity, auth_header, process_activity)
            )
        finally:
            loop.close()

        return "", 200
    except Exception as e:
        error_msg = "Internal error" if SECURITY_MODE == "production" else str(e)
        print(f"Teams error: {e}", file=sys.stderr)
        return jsonify({"error": error_msg}), 500


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "security_mode": SECURITY_MODE,
        "platforms": {
            "slack": ENABLE_SLACK,
            "webex": ENABLE_WEBEX,
            "teams": ENABLE_TEAMS,
        }
    })


if __name__ == "__main__":
    print("=" * 70)
    print(f"🔒 Unified Webhook Server - {SECURITY_MODE.upper()} MODE")
    print("=" * 70)
    print(f"Host: {HOST}")
    print(f"Port: {PORT}")
    print(f"Debug: {DEBUG}")
    print(f"\nEnabled Platforms:")
    print(f"  • Slack:  {'✅' if ENABLE_SLACK else '❌'}")
    print(f"  • Webex:  {'✅' if ENABLE_WEBEX else '❌'}")
    print(f"  • Teams:  {'✅' if ENABLE_TEAMS else '❌'}")

    if SECURITY_MODE == "local":
        print("\n🌐 WEB SERVICE HOSTED MODE (ngrok)")
        print("   Use ngrok traffic policy for signature verification")
    else:
        print("\n🔐 SELF-HOSTED MODE")
        print(f"   Rate limiting: {RATE_LIMIT_MAX_REQUESTS} req/{RATE_LIMIT_WINDOW}s")

    print("\n📝 Webhook URLs:")
    base_url = "https://your-url" if SECURITY_MODE == "production" else "https://your-ngrok-url.ngrok.io"
    if ENABLE_SLACK:
        print(f"   Slack:  {base_url}/slack/interactive")
    if ENABLE_WEBEX:
        print(f"   Webex:  {base_url}/webex/interactive")
    if ENABLE_TEAMS:
        print(f"   Teams:  {base_url}/api/messages")

    print("=" * 70)
    print()

    app.run(port=PORT, debug=DEBUG, host=HOST, use_reloader=False)
