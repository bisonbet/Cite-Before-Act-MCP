"""Mutating tool detection engine with multiple strategies."""

from typing import List, Optional, Set
from enum import Enum


class DetectionStrategy(Enum):
    """Detection strategies available."""

    ALLOWLIST = "allowlist"
    BLOCKLIST = "blocklist"
    CONVENTION = "convention"
    METADATA = "metadata"


class DetectionEngine:
    """Multi-strategy engine for detecting mutating tools."""

    # Common read-only prefixes (these are automatically non-mutating)
    READ_ONLY_PREFIXES = {
        "get_",
        "read_",
        "list_",
        "search_",
        "find_",
        "query_",
        "fetch_",
        "retrieve_",
        "show_",
        "display_",
        "view_",
        "describe_",
        "info_",
        "status_",
        "check_",
        "verify_",
        "validate_",
        "exists_",
        "count_",
        "stat_",
    }

    # Common read-only suffixes
    READ_ONLY_SUFFIXES = {
        "_get",
        "_read",
        "_list",
        "_search",
        "_find",
        "_query",
        "_fetch",
        "_retrieve",
        "_show",
        "_display",
        "_view",
        "_describe",
        "_info",
        "_status",
        "_check",
        "_verify",
        "_validate",
    }

    # Keywords in descriptions that suggest read-only operations
    READ_ONLY_KEYWORDS = {
        "read",
        "get",
        "list",
        "search",
        "find",
        "query",
        "fetch",
        "retrieve",
        "show",
        "display",
        "view",
        "describe",
        "info",
        "information",
        "status",
        "check",
        "verify",
        "validate",
        "exists",
        "count",
        "stat",
        "statistics",
        "read-only",
        "readonly",
    }

    # Common mutating prefixes
    MUTATING_PREFIXES = {
        # File/resource operations
        "delete_",
        "remove_",
        "update_",
        "create_",
        "write_",
        "edit_",
        "modify_",
        "move_",
        "copy_",
        "append_",
        "erase_",
        # Communication operations
        "send_",
        "email_",
        "message_",
        "tweet_",
        "post_",
        "share_",
        "publish_",
        "notify_",
        "broadcast_",
        "dm_",
        "sms_",
        # Payment/transaction operations
        "charge_",
        "payment_",
        "transaction_",
        "purchase_",
        "refund_",
        # HTTP/API operations
        "put_",
        "patch_",
    }

    # Common mutating suffixes
    MUTATING_SUFFIXES = {
        # File/resource operations
        "_delete",
        "_remove",
        "_update",
        "_create",
        "_write",
        "_edit",
        "_modify",
        # Communication operations
        "_send",
        "_email",
        "_message",
        "_tweet",
        "_post",
        "_share",
        "_publish",
        "_notify",
        "_broadcast",
        # Payment/transaction operations
        "_charge",
        "_payment",
        "_transaction",
        "_purchase",
    }

    # Keywords in descriptions that suggest mutation
    MUTATING_KEYWORDS = {
        # General mutation
        "mutate",
        "change",
        "alter",
        # File/resource operations
        "delete",
        "remove",
        "create",
        "write",
        "update",
        "modify",
        "edit",
        "destroy",
        "erase",
        "overwrite",
        "append",
        "move",
        "rename",
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
        "dm",
        "direct message",
        "sms",
        "text",
        # Payment/transaction operations
        "charge",
        "payment",
        "transaction",
        "purchase",
        "refund",
        "bill",
        "invoice",
        # Social media
        "social media",
        "social",
        "media",
    }

    def __init__(
        self,
        allowlist: Optional[List[str]] = None,
        blocklist: Optional[List[str]] = None,
        enable_convention: bool = True,
        enable_metadata: bool = True,
    ):
        """Initialize detection engine.

        Args:
            allowlist: Explicit list of tool names that are mutating
            blocklist: Explicit list of tool names that are NOT mutating
            enable_convention: Enable convention-based detection (prefixes/suffixes)
            enable_metadata: Enable metadata-based detection (description keywords)
        """
        self.allowlist: Set[str] = set(allowlist or [])
        self.blocklist: Set[str] = set(blocklist or [])
        self.enable_convention = enable_convention
        self.enable_metadata = enable_metadata

    def is_mutating(
        self,
        tool_name: str,
        tool_description: Optional[str] = None,
        tool_schema: Optional[dict] = None,
    ) -> bool:
        """Check if a tool is mutating using all enabled strategies.

        Args:
            tool_name: Name of the tool
            tool_description: Optional description of the tool
            tool_schema: Optional JSON schema of the tool

        Returns:
            True if tool is detected as mutating, False otherwise
        """
        # Check blocklist first (explicit non-mutating - highest priority override)
        if self.blocklist and tool_name in self.blocklist:
            import sys
            print(f"[DEBUG] Tool '{tool_name}' is in blocklist - non-mutating", file=sys.stderr)
            return False

        # Check for read-only patterns (automatic non-mutating detection)
        # This should come before mutating detection to catch read-only operations
        if self._check_read_only(tool_name, tool_description, tool_schema):
            import sys
            print(f"[DEBUG] Tool '{tool_name}' detected as read-only - non-mutating", file=sys.stderr)
            return False

        # Check allowlist (explicit mutating - high priority)
        if self.allowlist and tool_name in self.allowlist:
            import sys
            print(f"[DEBUG] Tool '{tool_name}' is in allowlist - mutating", file=sys.stderr)
            return True

        # Convention-based detection for mutating (works for any tool)
        if self.enable_convention and self._check_convention(tool_name):
            import sys
            print(f"[DEBUG] Tool '{tool_name}' detected as mutating via convention (prefix/suffix)", file=sys.stderr)
            return True

        # Metadata-based detection for mutating (works for any tool)
        if self.enable_metadata:
            description = tool_description or ""
            if tool_schema:
                description += " " + str(tool_schema.get("description", ""))
            if self._check_metadata(description):
                import sys
                print(f"[DEBUG] Tool '{tool_name}' detected as mutating via metadata (description keywords)", file=sys.stderr)
                return True

        # Default: if no strategies match, assume non-mutating (safe default)
        # Note: Allowlist is additive - it doesn't prevent convention/metadata detection
        import sys
        print(f"[DEBUG] Tool '{tool_name}' - no detection match, defaulting to non-mutating", file=sys.stderr)
        return False

    def _check_read_only(
        self,
        tool_name: str,
        tool_description: Optional[str] = None,
        tool_schema: Optional[dict] = None,
    ) -> bool:
        """Check if tool is read-only using naming conventions and metadata.

        Args:
            tool_name: Name of the tool
            tool_description: Optional description of the tool
            tool_schema: Optional JSON schema of the tool

        Returns:
            True if tool appears to be read-only, False otherwise
        """
        tool_name_lower = tool_name.lower()

        # Check read-only prefixes
        for prefix in self.READ_ONLY_PREFIXES:
            if tool_name_lower.startswith(prefix):
                return True

        # Check read-only suffixes
        for suffix in self.READ_ONLY_SUFFIXES:
            if tool_name_lower.endswith(suffix):
                return True

        # Check description for read-only keywords
        description = tool_description or ""
        if tool_schema:
            description += " " + str(tool_schema.get("description", ""))
        
        description_lower = description.lower()
        for keyword in self.READ_ONLY_KEYWORDS:
            if keyword in description_lower:
                return True

        return False

    def _check_convention(self, tool_name: str) -> bool:
        """Check if tool name follows mutating conventions.

        Args:
            tool_name: Name of the tool

        Returns:
            True if tool name matches mutating conventions
        """
        tool_name_lower = tool_name.lower()

        # Check prefixes
        for prefix in self.MUTATING_PREFIXES:
            if tool_name_lower.startswith(prefix):
                return True

        # Check suffixes
        for suffix in self.MUTATING_SUFFIXES:
            if tool_name_lower.endswith(suffix):
                return True

        return False

    def _check_metadata(self, description: str) -> bool:
        """Check if tool description contains mutating keywords.

        Args:
            description: Tool description text

        Returns:
            True if description contains mutating keywords
        """
        description_lower = description.lower()

        for keyword in self.MUTATING_KEYWORDS:
            if keyword in description_lower:
                return True

        return False

    def add_to_allowlist(self, tool_name: str) -> None:
        """Add a tool to the allowlist.

        Args:
            tool_name: Name of the tool to add
        """
        self.allowlist.add(tool_name)

    def add_to_blocklist(self, tool_name: str) -> None:
        """Add a tool to the blocklist.

        Args:
            tool_name: Name of the tool to add
        """
        self.blocklist.add(tool_name)

    def remove_from_allowlist(self, tool_name: str) -> None:
        """Remove a tool from the allowlist.

        Args:
            tool_name: Name of the tool to remove
        """
        self.allowlist.discard(tool_name)

    def remove_from_blocklist(self, tool_name: str) -> None:
        """Remove a tool from the blocklist.

        Args:
            tool_name: Name of the tool to remove
        """
        self.blocklist.discard(tool_name)

