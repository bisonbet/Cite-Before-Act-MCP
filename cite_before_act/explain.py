"""Generate natural language previews of tool actions."""

import json
from typing import Any, Dict, Optional


class ExplainEngine:
    """Engine for generating human-readable descriptions of tool actions."""

    def explain(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        tool_description: Optional[str] = None,
    ) -> str:
        """Generate a natural language description of what a tool would do.

        Args:
            tool_name: Name of the tool
            arguments: Arguments that would be passed to the tool
            tool_description: Optional description of the tool

        Returns:
            Human-readable description of the action
        """
        # Start with action description
        action = self._describe_action(tool_name, tool_description)

        # Add parameter details
        params_desc = self._describe_parameters(arguments)

        # Combine into natural language
        if params_desc:
            description = f"This will {action} with parameters: {params_desc}."
        else:
            description = f"This will {action}."

        # Add impact assessment if possible
        impact = self._assess_impact(tool_name, arguments)
        if impact:
            description += f" Impact: {impact}"

        return description

    def _describe_action(self, tool_name: str, tool_description: Optional[str]) -> str:
        """Describe the action the tool performs.

        Args:
            tool_name: Name of the tool
            tool_description: Optional description of the tool

        Returns:
            Natural language description of the action
        """
        # Use description if available
        if tool_description:
            # Extract action verb from description
            desc_lower = tool_description.lower()
            for verb in [
                "create",
                "delete",
                "write",
                "read",
                "update",
                "modify",
                "send",
                "charge",
                "move",
                "copy",
                "edit",
            ]:
                if verb in desc_lower:
                    # Try to extract a more complete phrase
                    idx = desc_lower.find(verb)
                    if idx > 0:
                        # Get context around the verb
                        start = max(0, idx - 20)
                        end = min(len(desc_lower), idx + 50)
                        snippet = desc_lower[start:end].strip()
                        # Clean up
                        snippet = snippet.split(".")[0].split(",")[0]
                        return snippet

        # Fall back to tool name analysis
        tool_lower = tool_name.lower()

        # Check for common patterns
        if "write" in tool_lower or "create" in tool_lower:
            return "create or write to a file or resource"
        elif "delete" in tool_lower or "remove" in tool_lower:
            return "delete or remove a file or resource"
        elif "update" in tool_lower or "modify" in tool_lower or "edit" in tool_lower:
            return "update or modify an existing file or resource"
        elif "send" in tool_lower:
            return "send a message or notification"
        elif "charge" in tool_lower:
            return "charge a payment or transaction"
        elif "move" in tool_lower:
            return "move or rename a file or resource"
        elif "copy" in tool_lower:
            return "copy a file or resource"
        else:
            return f"execute the '{tool_name}' operation"

    def _describe_parameters(self, arguments: Dict[str, Any]) -> str:
        """Describe the parameters in a human-readable way.

        Args:
            arguments: Dictionary of arguments

        Returns:
            Natural language description of parameters
        """
        if not arguments:
            return "no parameters"

        param_descriptions = []

        for key, value in arguments.items():
            # Format value appropriately
            if isinstance(value, str):
                # Truncate long strings
                if len(value) > 50:
                    value_str = value[:47] + "..."
                else:
                    value_str = value
                param_descriptions.append(f"{key}='{value_str}'")
            elif isinstance(value, (int, float, bool)):
                param_descriptions.append(f"{key}={value}")
            elif isinstance(value, list):
                if len(value) > 3:
                    param_descriptions.append(f"{key}=[{len(value)} items]")
                else:
                    param_descriptions.append(f"{key}={value}")
            elif isinstance(value, dict):
                param_descriptions.append(f"{key}={{...}}")
            else:
                param_descriptions.append(f"{key}={str(value)[:30]}")

        return ", ".join(param_descriptions)

    def _assess_impact(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[str]:
        """Assess the potential impact of the action.

        Args:
            tool_name: Name of the tool
            arguments: Arguments that would be passed

        Returns:
            Description of potential impact, or None if unclear
        """
        tool_lower = tool_name.lower()

        # File operations
        if any(op in tool_lower for op in ["write", "create", "file"]):
            if "path" in arguments or "file" in arguments:
                path = arguments.get("path") or arguments.get("file", "unknown")
                return f"will create or modify file at {path}"

        if "delete" in tool_lower or "remove" in tool_lower:
            if "path" in arguments or "file" in arguments:
                path = arguments.get("path") or arguments.get("file", "unknown")
                return f"will permanently delete {path}"

        # Email/messaging
        if "send" in tool_lower:
            if "to" in arguments or "recipient" in arguments:
                recipient = arguments.get("to") or arguments.get("recipient", "unknown")
                return f"will send message to {recipient}"

        # Payment
        if "charge" in tool_lower or "payment" in tool_lower:
            if "amount" in arguments:
                amount = arguments.get("amount", "unknown")
                return f"will charge amount {amount}"

        # Directory operations
        if "directory" in tool_lower or "folder" in tool_lower:
            if "path" in arguments:
                path = arguments.get("path", "unknown")
                return f"will affect directory at {path}"

        return None

