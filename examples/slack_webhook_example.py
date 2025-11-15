"""Example: Setting up Slack webhook for receiving approval responses.

This shows how to set up a Flask endpoint to receive Slack interactions.
The webhook must be publicly accessible (use ngrok for local testing).

Usage:
    1. Install Flask: pip install flask
    2. Set environment variables:
       - SLACK_BOT_TOKEN: Your Slack bot token
       - (Optional) PORT: Port to run on (default: 3000)
    3. Run: python examples/slack_webhook_example.py
    4. Expose with ngrok: ngrok http 3000
    5. Configure in Slack: Interactive Components -> Request URL = https://your-ngrok-url.ngrok.io/slack/interactive
"""

import json
import os
import sys
from flask import Flask, request, jsonify
from slack_sdk import WebClient
from cite_before_act.slack.handlers import SlackHandler

app = Flask(__name__)

# Initialize Slack client and handler
slack_token = os.getenv("SLACK_BOT_TOKEN")
if not slack_token:
    print("Error: SLACK_BOT_TOKEN environment variable not set", file=sys.stderr)
    sys.exit(1)

slack_client = WebClient(token=slack_token)
handler = SlackHandler(client=slack_client)


def write_approval_response(approval_id: str, approved: bool) -> None:
    """Write approval response to a file that the MCP server can read.
    
    This allows the webhook server (separate process) to communicate
    with the MCP server (running in Claude Desktop).
    
    Args:
        approval_id: Unique approval ID
        approved: Whether the action was approved
    """
    import time
    
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
    # Slack sends data as form-encoded
    payload = request.form.get("payload")
    if not payload:
        return jsonify({"error": "No payload"}), 400

    try:
        # Parse payload to extract approval info
        if isinstance(payload, str):
            payload_dict = json.loads(payload)
        else:
            payload_dict = payload
        
        # Handle the interaction
        response = handler.handle_interaction(payload_dict)
        
        # Also write approval response to file for MCP server
        actions = payload_dict.get("actions", [])
        for action in actions:
            action_id = action.get("action_id")
            value = action.get("value")
            if action_id in ("approve_action", "reject_action") and value:
                try:
                    value_data = json.loads(value) if isinstance(value, str) else value
                    approval_id = value_data.get("approval_id")
                    if approval_id:
                        approved = action_id == "approve_action"
                        write_approval_response(approval_id, approved)
                except Exception as e:
                    print(f"Error writing approval response: {e}", file=sys.stderr, flush=True)
        
        return jsonify(response)
    except Exception as e:
        print(f"Error handling interaction: {e}", file=sys.stderr, flush=True)
        return jsonify({"text": f"Error: {str(e)}"}), 500


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    print(f"Starting Slack webhook server on port {port}")
    print(f"Configure Slack Interactive Components URL to: http://localhost:{port}/slack/interactive")
    print(f"For production, use ngrok: ngrok http {port}")
    app.run(port=port, debug=True)

