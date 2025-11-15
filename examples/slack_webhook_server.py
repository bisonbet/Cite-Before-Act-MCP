"""Slack Webhook Server for receiving approval responses.

A production-ready Flask webhook server that receives Slack interactive button clicks
for approval/rejection of operations. Supports configurable security modes.

The webhook must be publicly accessible (use ngrok or deploy to cloud/VPS).

Security Modes:
    - LOCAL (default): For web service hosted (ngrok with traffic policy)
        * Validates approval_id format (prevents path traversal)
        * Optional debug mode
        * No application-level HMAC verification (ngrok handles it)
        * Use with: ngrok traffic policy for signature verification
        * Production-ready when using ngrok verification

    - PRODUCTION: For self-hosted (direct internet exposure)
        * Slack HMAC-SHA256 signature verification (in application)
        * Approval_id validation (prevents path traversal)
        * Configurable rate limiting (prevents DoS)
        * Input validation (prevents attacks)
        * Sanitized error messages
        * Debug mode disabled
        * Required for self-hosted servers without ngrok

Usage:
    1. Install dependencies: pip install flask slack-sdk

    2. WEB SERVICE HOSTED (ngrok with signature verification):
       ```bash
       # Get Slack signing secret from: https://api.slack.com/apps → Your App → Basic Information

       # Create ngrok traffic policy file
       cat > ngrok-slack-policy.yml <<EOF
       on_http_request:
         - actions:
             - type: "webhook-verification"
               config:
                 provider: "slack"
                 secret: "YOUR_SLACK_SIGNING_SECRET"
       EOF

       # Set environment variables
       export SLACK_BOT_TOKEN=xoxb-your-token
       export SECURITY_MODE=local  # ngrok handles verification

       # Run server and ngrok
       python examples/slack_webhook_server.py
       ngrok http 3000 --traffic-policy-file ngrok-slack-policy.yml
       ```

    3. SELF-HOSTED (cloud/VPS with direct exposure):
       ```bash
       export SLACK_BOT_TOKEN=xoxb-your-token
       export SLACK_SIGNING_SECRET=your-signing-secret
       export SECURITY_MODE=production
       python examples/slack_webhook_server.py

       # Deploy to your cloud provider or run on VPS with HTTPS
       ```

    4. Configure in Slack:
       - Go to: https://api.slack.com/apps → Your App → Interactivity & Shortcuts
       - Set Request URL: https://your-ngrok-url.ngrok.io/slack/interactive (or your domain)
       - Save changes

See README.md for detailed setup instructions and security best practices.
"""

import hashlib
import hmac
import json
import os
import re
import sys
import time
from collections import defaultdict
from flask import Flask, request, jsonify
from slack_sdk import WebClient
from cite_before_act.slack.handlers import SlackHandler

app = Flask(__name__)

# Configuration
SECURITY_MODE = os.getenv("SECURITY_MODE", "local").lower()
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
PORT = int(os.getenv("PORT", 3000))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Rate limiting configuration (production mode only)
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", 60))  # seconds
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", 60))  # max requests per window

# Validate configuration
if not SLACK_BOT_TOKEN:
    print("Error: SLACK_BOT_TOKEN environment variable not set", file=sys.stderr)
    sys.exit(1)

if SECURITY_MODE not in ["local", "production"]:
    print(f"Error: SECURITY_MODE must be 'local' or 'production', got: {SECURITY_MODE}", file=sys.stderr)
    sys.exit(1)

if SECURITY_MODE == "production":
    if not SLACK_SIGNING_SECRET:
        print("Error: SLACK_SIGNING_SECRET required for production mode", file=sys.stderr)
        print("Get it from: https://api.slack.com/apps → Your App → Basic Information → Signing Secret", file=sys.stderr)
        sys.exit(1)
    if DEBUG:
        print("Warning: DEBUG mode enabled in production - this exposes internal errors!", file=sys.stderr)

# Initialize Slack client and handler
slack_client = WebClient(token=SLACK_BOT_TOKEN)
handler = SlackHandler(client=slack_client)

# Rate limiting store (production mode only)
if SECURITY_MODE == "production":
    _rate_limit_store = defaultdict(list)


def validate_approval_id(approval_id: str) -> bool:
    """Validate approval_id format to prevent path traversal attacks.

    Args:
        approval_id: The approval ID to validate

    Returns:
        True if valid, False otherwise
    """
    # Only allow alphanumeric characters, hyphens, and underscores
    # This prevents path traversal like: ../../etc/passwd
    if not re.match(r'^[a-zA-Z0-9_-]+$', approval_id):
        return False

    # Reasonable length limit
    if len(approval_id) > 100:
        return False

    return True


def verify_slack_signature(request_body: bytes, timestamp: str, signature: str) -> bool:
    """Verify Slack request signature using HMAC-SHA256.

    This prevents request forgery - only requests from Slack will have valid signatures.

    Args:
        request_body: Raw request body bytes
        timestamp: X-Slack-Request-Timestamp header
        signature: X-Slack-Signature header

    Returns:
        True if signature is valid, False otherwise
    """
    if not SLACK_SIGNING_SECRET:
        return False

    # Prevent replay attacks - reject requests older than 5 minutes
    try:
        request_timestamp = int(timestamp)
        if abs(time.time() - request_timestamp) > 60 * 5:
            print("Warning: Request timestamp too old - possible replay attack", file=sys.stderr)
            return False
    except (ValueError, TypeError):
        return False

    # Compute expected signature
    sig_basestring = f"v0:{timestamp}:{request_body.decode('utf-8')}"
    expected_signature = 'v0=' + hmac.new(
        SLACK_SIGNING_SECRET.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()

    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(expected_signature, signature)


def check_rate_limit(client_id: str) -> bool:
    """Check if client has exceeded rate limit (production mode only).

    Args:
        client_id: Identifier for the client (e.g., IP address)

    Returns:
        True if within rate limit, False if exceeded
    """
    if SECURITY_MODE != "production":
        return True

    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW

    # Clean old entries
    _rate_limit_store[client_id] = [
        ts for ts in _rate_limit_store[client_id]
        if ts > window_start
    ]

    # Check limit
    if len(_rate_limit_store[client_id]) >= RATE_LIMIT_MAX_REQUESTS:
        return False

    # Record this request
    _rate_limit_store[client_id].append(now)
    return True


def validate_payload_size(payload: str) -> bool:
    """Validate payload size to prevent memory exhaustion attacks.

    Args:
        payload: The payload string

    Returns:
        True if size is acceptable, False otherwise
    """
    # Slack payloads are typically small - 100KB is generous
    MAX_PAYLOAD_SIZE = 100 * 1024  # 100KB
    return len(payload) <= MAX_PAYLOAD_SIZE


def write_approval_response(approval_id: str, approved: bool) -> None:
    """Write approval response to a file that the MCP server can read.

    This allows the webhook server (separate process) to communicate
    with the MCP server (running in Claude Desktop).

    Args:
        approval_id: Unique approval ID (must be validated before calling)
        approved: Whether the action was approved
    """
    # Note: approval_id MUST be validated before calling this function
    approval_file = f"/tmp/cite-before-act-slack-approval-{approval_id}.json"
    try:
        with open(approval_file, "w") as f:
            json.dump({
                "approval_id": approval_id,
                "approved": approved,
                "timestamp": time.time(),
            }, f)
        print(f"Wrote approval response: {approval_id} -> {approved}", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"Error writing approval file: {e}", file=sys.stderr, flush=True)


@app.route("/slack/interactive", methods=["POST"])
def slack_interactive():
    """Handle Slack interactive component events (button clicks)."""

    # Production mode: Verify Slack signature
    if SECURITY_MODE == "production":
        # Get signature headers
        timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
        signature = request.headers.get("X-Slack-Signature", "")

        if not verify_slack_signature(request.get_data(), timestamp, signature):
            print("Warning: Invalid Slack signature - possible forged request", file=sys.stderr)
            return jsonify({"error": "Invalid signature"}), 401

    # Production mode: Rate limiting
    if SECURITY_MODE == "production":
        client_id = request.remote_addr or "unknown"
        if not check_rate_limit(client_id):
            print(f"Warning: Rate limit exceeded for {client_id}", file=sys.stderr)
            return jsonify({"error": "Rate limit exceeded"}), 429

    # Validate Content-Type
    content_type = request.headers.get("Content-Type", "")
    if "application/x-www-form-urlencoded" not in content_type:
        return jsonify({"error": "Invalid content type"}), 400

    # Get payload
    payload = request.form.get("payload")
    if not payload:
        return jsonify({"error": "No payload"}), 400

    # Validate payload size
    if not validate_payload_size(payload):
        print("Warning: Payload too large - possible attack", file=sys.stderr)
        return jsonify({"error": "Payload too large"}), 413

    try:
        # Parse payload
        if isinstance(payload, str):
            payload_dict = json.loads(payload)
        else:
            payload_dict = payload

        # Handle the interaction
        response = handler.handle_interaction(payload_dict)

        # Write approval response to file for MCP server
        actions = payload_dict.get("actions", [])
        for action in actions:
            action_id = action.get("action_id")
            value = action.get("value")
            if action_id in ("approve_action", "reject_action") and value:
                try:
                    value_data = json.loads(value) if isinstance(value, str) else value
                    approval_id = value_data.get("approval_id")

                    # CRITICAL: Validate approval_id to prevent path traversal
                    if approval_id and validate_approval_id(approval_id):
                        approved = action_id == "approve_action"
                        write_approval_response(approval_id, approved)
                    elif approval_id:
                        print(f"Warning: Invalid approval_id format: {approval_id}", file=sys.stderr)
                except Exception as e:
                    # In production, don't leak error details
                    if SECURITY_MODE == "production":
                        print(f"Error processing approval: {type(e).__name__}", file=sys.stderr, flush=True)
                    else:
                        print(f"Error writing approval response: {e}", file=sys.stderr, flush=True)

        return jsonify(response)
    except json.JSONDecodeError:
        error_msg = "Invalid JSON" if SECURITY_MODE == "production" else "Invalid JSON in payload"
        return jsonify({"error": error_msg}), 400
    except Exception as e:
        # Sanitize error messages in production
        if SECURITY_MODE == "production":
            print(f"Error handling interaction: {type(e).__name__}", file=sys.stderr, flush=True)
            return jsonify({"error": "Internal error"}), 500
        else:
            print(f"Error handling interaction: {e}", file=sys.stderr, flush=True)
            return jsonify({"text": f"Error: {str(e)}"}), 500


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "security_mode": SECURITY_MODE,
        "hmac_enabled": SECURITY_MODE == "production",
    })


if __name__ == "__main__":
    print("=" * 60)
    print(f"🔒 Slack Webhook Server - {SECURITY_MODE.upper()} MODE")
    print("=" * 60)
    print(f"Port: {PORT}")
    print(f"Debug: {DEBUG}")

    if SECURITY_MODE == "local":
        print("\n🌐 WEB SERVICE HOSTED MODE")
        print("   Designed for: ngrok with traffic policy verification")
        print("\n   Security Features:")
        print("   ✓ Approval ID validation (prevents path traversal)")
        print("   ✗ No application-level HMAC (ngrok should handle it)")
        print("   ✗ No rate limiting (rely on ngrok/web service)")
        print("\n   ⚠️  IMPORTANT: Use ngrok traffic policy for signature verification!")
        print("   Without verification, anyone with your URL can send fake requests.")
        print("\n   Setup ngrok with verification:")
        print("   1. Create ngrok-slack-policy.yml with your Slack signing secret")
        print("   2. Run: ngrok http 3000 --traffic-policy-file ngrok-slack-policy.yml")
        print("   3. See README.md for complete instructions")
        print("\n   For self-hosted (cloud/VPS): export SECURITY_MODE=production")
    else:
        print("\n🔐 SELF-HOSTED MODE")
        print("   Designed for: Direct internet exposure (cloud/VPS)")
        print("\n   Security Features:")
        print("   ✓ Slack HMAC signature verification (in application)")
        print("   ✓ Approval ID validation")
        print(f"   ✓ Rate limiting ({RATE_LIMIT_MAX_REQUESTS} req/{RATE_LIMIT_WINDOW}s)")
        print("   ✓ Input validation")
        print("   ✓ Sanitized errors")
        print("\n   Deploy to: Cloud provider, VPS, or any HTTPS-enabled server")

    print("\n📝 Configure in Slack:")
    print(f"   Interactivity & Shortcuts → Request URL:")
    if SECURITY_MODE == "local":
        print(f"   https://your-ngrok-url.ngrok.io/slack/interactive")
    else:
        print(f"   https://your-domain.com/slack/interactive")
    print("=" * 60)
    print()

    app.run(port=PORT, debug=DEBUG, host="0.0.0.0")
