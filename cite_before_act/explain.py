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

        # Get impact assessment first (includes key details like file path)
        impact = self._assess_impact(tool_name, arguments)
        
        # For file write operations, create a concise, natural description
        if "write" in tool_name.lower() or "create" in tool_name.lower():
            if "content" in arguments and isinstance(arguments["content"], str):
                content = arguments["content"]
                lines = content.split("\n")
                char_count = len(content)
                
                # Get file path
                path = arguments.get("path") or arguments.get("file", "unknown file")
                
                # Build natural description
                if char_count > 100:
                    # Long content - summarize
                    if len(lines) > 1:
                        description = f"Write {len(lines)} lines ({char_count:,} characters) to {path}"
                    else:
                        description = f"Write {char_count:,} characters to {path}"
                else:
                    # Short content - show preview (single line for dialog compatibility)
                    first_line = lines[0] if lines else content
                    if len(first_line) > 60:
                        preview = first_line[:57] + "..."
                    else:
                        preview = first_line
                    # Use single line format for better dialog display
                    description = f"Write to {path}: {preview}"
                
                return description

        # For communication operations, use impact description directly (it's already well-formatted)
        tool_lower = tool_name.lower()
        if any(op in tool_lower for op in ["email", "tweet", "post", "send", "message", "dm", "share", "notify", "broadcast"]):
            if impact:
                # Impact already contains a well-formatted description
                return impact
            # Fall through to general handling if no impact

        # For payment operations, use impact description directly
        if any(op in tool_lower for op in ["charge", "payment", "transaction", "purchase"]):
            if impact:
                return impact

        # For other operations, use concise parameter summary
        params_desc = self._describe_parameters(arguments, tool_name)
        
        # Build concise description
        if impact:
            # Impact already includes key details, so keep description simple
            description = f"{action}"
            # Add impact details if not redundant
            if "path" in arguments or "file" in arguments:
                path = arguments.get("path") or arguments.get("file", "")
                if path and path not in impact:
                    description += f" at {path}"
            else:
                description += f" - {impact}"
        elif params_desc and params_desc != "no parameters":
            # Only show key parameters, not all of them
            description = f"{action} ({params_desc})"
        else:
            description = f"{action}"

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
                # File/resource operations
                "create",
                "delete",
                "write",
                "read",
                "update",
                "modify",
                "move",
                "copy",
                "edit",
                # Communication operations
                "send",
                "email",
                "message",
                "tweet",
                "post",
                "share",
                "publish",
                "notify",
                "broadcast",
                # Payment/transaction operations
                "charge",
                "payment",
                "transaction",
                "purchase",
            ]:
                if verb in desc_lower:
                    # Try to extract a more complete phrase
                    idx = desc_lower.find(verb)
                    if idx >= 0:
                        # Get context around the verb, ensuring we don't cut off the verb itself
                        # Start from the beginning of the sentence or a reasonable point before the verb
                        sentence_start = desc_lower.rfind(".", 0, idx)
                        if sentence_start < 0:
                            sentence_start = desc_lower.rfind(" ", 0, max(0, idx - 30))
                        if sentence_start < 0:
                            sentence_start = 0
                        else:
                            sentence_start += 1  # Skip the period/space
                        
                        # End at sentence end or reasonable limit
                        sentence_end = desc_lower.find(".", idx)
                        if sentence_end < 0:
                            sentence_end = min(len(desc_lower), idx + 100)
                        else:
                            sentence_end += 1  # Include the period
                        
                        snippet = desc_lower[sentence_start:sentence_end].strip()
                        # Clean up - remove extra whitespace
                        snippet = " ".join(snippet.split())
                        # Capitalize first letter
                        if snippet:
                            snippet = snippet[0].upper() + snippet[1:] if len(snippet) > 1 else snippet.upper()
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
        elif "email" in tool_lower:
            return "send an email message"
        elif "tweet" in tool_lower:
            return "post a tweet to Twitter/X"
        elif "post" in tool_lower and ("social" in tool_lower or "media" in tool_lower):
            return "post to social media"
        elif "post" in tool_lower:
            return "create or publish a post"
        elif "send" in tool_lower:
            return "send a message or notification"
        elif "message" in tool_lower or "dm" in tool_lower:
            return "send a direct message"
        elif "share" in tool_lower:
            return "share content or information"
        elif "publish" in tool_lower:
            return "publish content"
        elif "notify" in tool_lower or "broadcast" in tool_lower:
            return "send a notification or broadcast"
        elif "charge" in tool_lower or "payment" in tool_lower or "transaction" in tool_lower:
            return "process a payment or transaction"
        elif "purchase" in tool_lower:
            return "make a purchase"
        elif "move" in tool_lower:
            return "move or rename a file or resource"
        elif "copy" in tool_lower:
            return "copy a file or resource"
        else:
            return f"execute the '{tool_name}' operation"

    def _describe_parameters(self, arguments: Dict[str, Any], tool_name: str = "") -> str:
        """Describe the parameters in a human-readable way.

        Args:
            arguments: Dictionary of arguments
            tool_name: Name of the tool (for context-aware summarization)

        Returns:
            Natural language description of parameters
        """
        if not arguments:
            return "no parameters"

        param_descriptions = []
        tool_lower = tool_name.lower()

        for key, value in arguments.items():
            # Skip content parameter for file operations (handled separately in explain())
            if key == "content" and ("write" in tool_lower or "create" in tool_lower):
                continue
            
            # Format value appropriately
            if isinstance(value, str):
                # For long strings, summarize instead of truncating
                if len(value) > 100:
                    # Count lines and characters
                    lines = value.split("\n")
                    if len(lines) > 1:
                        value_str = f"{len(lines)} lines, {len(value)} characters"
                    else:
                        value_str = f"{len(value)} characters"
                    param_descriptions.append(f"{key}: {value_str}")
                elif len(value) > 50:
                    # Medium length - show first part
                    value_str = value[:47] + "..."
                    param_descriptions.append(f"{key}: '{value_str}'")
                else:
                    param_descriptions.append(f"{key}: '{value}'")
            elif isinstance(value, (int, float, bool)):
                param_descriptions.append(f"{key}: {value}")
            elif isinstance(value, list):
                if len(value) > 3:
                    param_descriptions.append(f"{key}: {len(value)} items")
                else:
                    param_descriptions.append(f"{key}: {value}")
            elif isinstance(value, dict):
                param_descriptions.append(f"{key}: {{...}}")
            else:
                str_value = str(value)
                if len(str_value) > 30:
                    param_descriptions.append(f"{key}: {str_value[:27]}...")
                else:
                    param_descriptions.append(f"{key}: {str_value}")

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
                return f"file: {path}"

        if "delete" in tool_lower or "remove" in tool_lower:
            if "path" in arguments or "file" in arguments:
                path = arguments.get("path") or arguments.get("file", "unknown")
                return f"will permanently delete {path}"

        # Email operations
        if "email" in tool_lower:
            recipient = arguments.get("to") or arguments.get("recipient") or arguments.get("email", "unknown")
            subject = arguments.get("subject", "")
            if subject:
                return f"will send email to {recipient}: {subject}"
            return f"will send email to {recipient}"
        
        # Social media posts
        if "tweet" in tool_lower:
            text = arguments.get("text") or arguments.get("content", "")
            if text and len(text) > 50:
                return f"will post tweet: {text[:47]}..."
            elif text:
                return f"will post tweet: {text}"
            return "will post a tweet"
        
        if "post" in tool_lower and ("social" in tool_lower or "media" in tool_lower):
            platform = arguments.get("platform", "social media")
            text = arguments.get("text") or arguments.get("content", "")
            if text and len(text) > 50:
                return f"will post to {platform}: {text[:47]}..."
            elif text:
                return f"will post to {platform}: {text}"
            return f"will post to {platform}"
        
        # Messaging (general)
        if "send" in tool_lower or "message" in tool_lower or "dm" in tool_lower:
            recipient = arguments.get("to") or arguments.get("recipient") or arguments.get("user", "unknown")
            text = arguments.get("text") or arguments.get("content") or arguments.get("message", "")
            if text and len(text) > 50:
                return f"will send message to {recipient}: {text[:47]}..."
            elif text:
                return f"will send message to {recipient}: {text}"
            return f"will send message to {recipient}"

        # Payment/transaction operations
        if "charge" in tool_lower or "payment" in tool_lower or "transaction" in tool_lower:
            amount = arguments.get("amount") or arguments.get("value", "unknown")
            currency = arguments.get("currency", "")
            if currency:
                return f"will process payment of {amount} {currency}"
            return f"will process payment of {amount}"
        
        if "purchase" in tool_lower:
            amount = arguments.get("amount") or arguments.get("price", "unknown")
            item = arguments.get("item") or arguments.get("product", "")
            if item:
                return f"will purchase {item} for {amount}"
            return f"will make purchase for {amount}"

        # Directory operations
        if "directory" in tool_lower or "folder" in tool_lower:
            if "path" in arguments:
                path = arguments.get("path", "unknown")
                return f"will affect directory at {path}"

        return None

