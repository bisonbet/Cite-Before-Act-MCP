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

    # Common mutating prefixes
    MUTATING_PREFIXES = {
        "send_",
        "delete_",
        "remove_",
        "charge_",
        "update_",
        "create_",
        "write_",
        "edit_",
        "modify_",
        "move_",
        "copy_",
        "append_",
        "erase_",
        "publish_",
        "post_",
        "put_",
        "patch_",
    }

    # Common mutating suffixes
    MUTATING_SUFFIXES = {
        "_delete",
        "_remove",
        "_update",
        "_create",
        "_write",
        "_edit",
        "_modify",
        "_send",
        "_charge",
    }

    # Keywords in descriptions that suggest mutation
    MUTATING_KEYWORDS = {
        "mutate",
        "delete",
        "remove",
        "create",
        "write",
        "update",
        "modify",
        "edit",
        "send",
        "charge",
        "publish",
        "post",
        "destroy",
        "erase",
        "overwrite",
        "append",
        "move",
        "rename",
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
        # Check allowlist first (highest priority)
        if self.allowlist and tool_name in self.allowlist:
            return True

        # Check blocklist (explicit non-mutating)
        if self.blocklist and tool_name in self.blocklist:
            return False

        # If blocklist exists and tool is not in it, and we have a blocklist strategy,
        # everything else is mutating
        if self.blocklist and not self.allowlist:
            return True

        # Convention-based detection
        if self.enable_convention and self._check_convention(tool_name):
            return True

        # Metadata-based detection
        if self.enable_metadata:
            description = tool_description or ""
            if tool_schema:
                description += " " + str(tool_schema.get("description", ""))
            if self._check_metadata(description):
                return True

        # Default: if allowlist exists and tool not in it, assume non-mutating
        if self.allowlist:
            return False

        # Default: if no strategies match, assume non-mutating (safe default)
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

