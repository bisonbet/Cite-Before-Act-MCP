"""Track approval message references across platforms for cross-platform updates."""

import json
import os
from typing import Optional, Dict, Any


def save_message_reference(
    approval_id: str,
    platform: str,
    message_data: Dict[str, Any]
) -> None:
    """
    Save a message reference for cross-platform updates.

    Args:
        approval_id: Unique approval ID
        platform: Platform name (slack, webex, teams)
        message_data: Platform-specific message reference data
            - Slack: {"ts": "1234567890.123456", "channel": "C123456"}
            - Webex: {"message_id": "Y2lzY29zcGFyazovL...", "room_id": "Y2lzY29..."}
            - Teams: {"activity_id": "...", "conversation_id": "19:..."}
    """
    ref_file = f"/tmp/cite-before-act-approval-{approval_id}-messages.json"

    # Load existing references
    references = {}
    if os.path.exists(ref_file):
        try:
            with open(ref_file, "r") as f:
                references = json.load(f)
        except Exception:
            pass

    # Add/update this platform's reference
    references[platform] = message_data

    # Save back
    try:
        with open(ref_file, "w") as f:
            json.dump(references, f)
    except Exception as e:
        print(f"Warning: Could not save message reference: {e}")


def get_message_references(approval_id: str) -> Dict[str, Dict[str, Any]]:
    """
    Get all message references for an approval.

    Args:
        approval_id: Unique approval ID

    Returns:
        Dictionary mapping platform names to message reference data
    """
    ref_file = f"/tmp/cite-before-act-approval-{approval_id}-messages.json"

    if not os.path.exists(ref_file):
        return {}

    try:
        with open(ref_file, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def clear_message_references(approval_id: str) -> None:
    """
    Clear message references after approval is complete.

    Args:
        approval_id: Unique approval ID
    """
    ref_file = f"/tmp/cite-before-act-approval-{approval_id}-messages.json"

    try:
        if os.path.exists(ref_file):
            os.remove(ref_file)
    except Exception:
        pass
