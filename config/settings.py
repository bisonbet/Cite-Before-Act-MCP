"""Configuration management for Cite-Before-Act MCP."""

import os
from typing import List, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator


# Load environment variables from .env file
load_dotenv()


class SlackConfig(BaseModel):
    """Slack configuration."""

    token: str = Field(..., description="Slack bot token (xoxb-...)")
    channel: Optional[str] = Field(None, description="Slack channel ID or name")
    user_id: Optional[str] = Field(None, description="Slack user ID for DMs")

    @field_validator("token")
    @classmethod
    def validate_token(cls, v: str) -> str:
        """Validate Slack token format."""
        if not v.startswith(("xoxb-", "xoxp-")):
            raise ValueError("Slack token must start with xoxb- or xoxp-")
        return v


class DetectionConfig(BaseModel):
    """Detection engine configuration."""

    allowlist: List[str] = Field(default_factory=list, description="Explicit mutating tools")
    blocklist: List[str] = Field(default_factory=list, description="Explicit non-mutating tools")
    enable_convention: bool = Field(True, description="Enable convention-based detection")
    enable_metadata: bool = Field(True, description="Enable metadata-based detection")


class UpstreamServerConfig(BaseModel):
    """Upstream MCP server configuration."""

    command: Optional[str] = Field(None, description="Command to run upstream server (stdio)")
    args: List[str] = Field(default_factory=list, description="Arguments for command")
    url: Optional[str] = Field(None, description="URL for upstream server (HTTP/SSE)")
    transport: str = Field("stdio", description="Transport type: stdio, http, or sse")

    @field_validator("transport")
    @classmethod
    def validate_transport(cls, v: str) -> str:
        """Validate transport type."""
        if v not in ("stdio", "http", "sse"):
            raise ValueError("Transport must be stdio, http, or sse")
        return v


class Settings(BaseModel):
    """Application settings."""

    slack: Optional[SlackConfig] = Field(None, description="Slack configuration")
    detection: DetectionConfig = Field(default_factory=DetectionConfig, description="Detection config")
    upstream: Optional[UpstreamServerConfig] = Field(None, description="Upstream server config")
    approval_timeout_seconds: int = Field(300, description="Default approval timeout")
    enable_slack: bool = Field(True, description="Enable Slack integration")

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables.

        Returns:
            Settings instance
        """
        # Slack config
        slack_token = os.getenv("SLACK_BOT_TOKEN")
        slack_channel = os.getenv("SLACK_CHANNEL")
        slack_user_id = os.getenv("SLACK_USER_ID")

        slack_config = None
        if slack_token:
            slack_config = SlackConfig(
                token=slack_token,
                channel=slack_channel,
                user_id=slack_user_id,
            )

        # Detection config
        allowlist_str = os.getenv("DETECTION_ALLOWLIST", "")
        blocklist_str = os.getenv("DETECTION_BLOCKLIST", "")
        allowlist = [t.strip() for t in allowlist_str.split(",") if t.strip()] if allowlist_str else []
        blocklist = [t.strip() for t in blocklist_str.split(",") if t.strip()] if blocklist_str else []

        detection_config = DetectionConfig(
            allowlist=allowlist,
            blocklist=blocklist,
            enable_convention=os.getenv("DETECTION_ENABLE_CONVENTION", "true").lower() == "true",
            enable_metadata=os.getenv("DETECTION_ENABLE_METADATA", "true").lower() == "true",
        )

        # Upstream server config
        upstream_command = os.getenv("UPSTREAM_COMMAND")
        upstream_args_str = os.getenv("UPSTREAM_ARGS", "")
        upstream_args = [a.strip() for a in upstream_args_str.split(",") if a.strip()] if upstream_args_str else []
        upstream_url = os.getenv("UPSTREAM_URL")
        upstream_transport = os.getenv("UPSTREAM_TRANSPORT", "stdio")

        upstream_config = None
        if upstream_command or upstream_url:
            upstream_config = UpstreamServerConfig(
                command=upstream_command,
                args=upstream_args,
                url=upstream_url,
                transport=upstream_transport,
            )

        return cls(
            slack=slack_config,
            detection=detection_config,
            upstream=upstream_config,
            approval_timeout_seconds=int(os.getenv("APPROVAL_TIMEOUT_SECONDS", "300")),
            enable_slack=os.getenv("ENABLE_SLACK", "true").lower() == "true",
        )


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance.

    Returns:
        Settings instance
    """
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
    return _settings


def set_settings(settings: Settings) -> None:
    """Set the global settings instance.

    Args:
        settings: Settings instance to use
    """
    global _settings
    _settings = settings

