"""Example: Setting up Slack webhook for receiving approval responses.

This shows how to set up a Flask/FastAPI endpoint to receive Slack interactions.
"""

from flask import Flask, request, jsonify
from cite_before_act.slack.handlers import SlackHandler

app = Flask(__name__)
handler = SlackHandler()


@app.route("/slack/interactive", methods=["POST"])
def slack_interactive():
    """Handle Slack interactive component events (button clicks)."""
    # Slack sends data as form-encoded
    payload = request.form.get("payload")
    if not payload:
        return jsonify({"error": "No payload"}), 400

    # Handle the interaction
    response = handler.handle_interaction(payload)

    return jsonify(response)


if __name__ == "__main__":
    # Run on port 3000 (Slack requires HTTPS in production, use ngrok for testing)
    app.run(port=3000, debug=True)

# To test locally:
# 1. Install Flask: pip install flask
# 2. Run: python examples/slack_webhook_example.py
# 3. Use ngrok to expose: ngrok http 3000
# 4. Set Slack app's Interactive Components URL to: https://your-ngrok-url.ngrok.io/slack/interactive

