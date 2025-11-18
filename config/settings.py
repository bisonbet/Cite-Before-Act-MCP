"""Configuration management for Cite-Before-Act MCP."""

import os
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator


# Load environment variables from .env file in project root
# This ensures .env is found regardless of the current working directory
_project_root = Path(__file__).parent.parent
_env_path = _project_root / ".env"
load_dotenv(_env_path)


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


class WebexConfig(BaseModel):
    """Webex Teams configuration."""

    token: str = Field(..., description="Webex bot access token")
    room_id: Optional[str] = Field(None, description="Webex room/space ID")
    person_email: Optional[str] = Field(None, description="Person email for DMs")


class TeamsConfig(BaseModel):
    """Microsoft Teams configuration."""

    app_id: str = Field(..., description="Microsoft App ID")
    app_password: str = Field(..., description="Microsoft App Password")
    service_url: str = Field("https://smba.trafficmanager.net/amer/", description="Teams service URL")
    conversation_id: Optional[str] = Field(None, description="Conversation/channel ID")
    tenant_id: Optional[str] = Field(None, description="Teams tenant ID")


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
    headers: Dict[str, str] = Field(default_factory=dict, description="HTTP headers for remote servers")

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
    webex: Optional[WebexConfig] = Field(None, description="Webex Teams configuration")
    teams: Optional[TeamsConfig] = Field(None, description="Microsoft Teams configuration")
    detection: DetectionConfig = Field(default_factory=DetectionConfig, description="Detection config")
    upstream: Optional[UpstreamServerConfig] = Field(None, description="Upstream server config")
    approval_timeout_seconds: int = Field(300, description="Default approval timeout")
    enable_slack: bool = Field(True, description="Enable Slack integration")
    enable_webex: bool = Field(False, description="Enable Webex Teams integration")
    enable_teams: bool = Field(False, description="Enable Microsoft Teams integration")
    use_local_approval: bool = Field(True, description="Enable local approval (GUI/file-based)")
    use_gui_approval: bool = Field(True, description="Use GUI dialog for local approval (requires tkinter)")

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

        # Webex config
        webex_token = os.getenv("WEBEX_BOT_TOKEN")
        webex_room_id = os.getenv("WEBEX_ROOM_ID")
        webex_person_email = os.getenv("WEBEX_PERSON_EMAIL")

        webex_config = None
        if webex_token:
            webex_config = WebexConfig(
                token=webex_token,
                room_id=webex_room_id,
                person_email=webex_person_email,
            )

        # Teams config
        teams_app_id = os.getenv("TEAMS_APP_ID")
        teams_app_password = os.getenv("TEAMS_APP_PASSWORD")
        teams_service_url = os.getenv("TEAMS_SERVICE_URL", "https://smba.trafficmanager.net/amer/")
        teams_conversation_id = os.getenv("TEAMS_CONVERSATION_ID")
        teams_tenant_id = os.getenv("TEAMS_TENANT_ID")

        teams_config = None
        if teams_app_id and teams_app_password:
            teams_config = TeamsConfig(
                app_id=teams_app_id,
                app_password=teams_app_password,
                service_url=teams_service_url,
                conversation_id=teams_conversation_id,
                tenant_id=teams_tenant_id,
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
        
        # Parse headers from environment variables
        # Format: UPSTREAM_HEADERS=Header1:value1,Header2:value2
        # Or individual: UPSTREAM_HEADER_Authorization=Bearer token
        upstream_headers: Dict[str, str] = {}
        upstream_headers_str = os.getenv("UPSTREAM_HEADERS", "")
        if upstream_headers_str:
            # Parse comma-separated header:value pairs
            for header_pair in upstream_headers_str.split(","):
                if ":" in header_pair:
                    key, value = header_pair.split(":", 1)
                    upstream_headers[key.strip()] = value.strip()
        
        # Also check for individual header environment variables (UPSTREAM_HEADER_*)
        for key, value in os.environ.items():
            if key.startswith("UPSTREAM_HEADER_"):
                header_name = key[len("UPSTREAM_HEADER_"):]
                upstream_headers[header_name] = value
        
        # Special handling for Authorization header from common env vars
        # Support both UPSTREAM_HEADER_Authorization and direct token vars
        auth_token = os.getenv("UPSTREAM_AUTH_TOKEN") or os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
        if auth_token and "Authorization" not in upstream_headers:
            # Check if token already has "Bearer " prefix
            if auth_token.startswith("Bearer "):
                upstream_headers["Authorization"] = auth_token
            else:
                upstream_headers["Authorization"] = f"Bearer {auth_token}"

        upstream_config = None
        if upstream_command or upstream_url:
            upstream_config = UpstreamServerConfig(
                command=upstream_command,
                args=upstream_args,
                url=upstream_url,
                transport=upstream_transport,
                headers=upstream_headers,
            )

        # Approval settings
        approval_timeout = int(os.getenv("APPROVAL_TIMEOUT_SECONDS", "300"))
        enable_slack = os.getenv("ENABLE_SLACK", "true").lower() == "true"
        enable_webex = os.getenv("ENABLE_WEBEX", "false").lower() == "true"
        enable_teams = os.getenv("ENABLE_TEAMS", "false").lower() == "true"
        use_local_approval = os.getenv("USE_LOCAL_APPROVAL", "true").lower() == "true"
        use_gui_approval = os.getenv("USE_GUI_APPROVAL", "true").lower() == "true"

        return cls(
            slack=slack_config,
            webex=webex_config,
            teams=teams_config,
            detection=detection_config,
            upstream=upstream_config,
            approval_timeout_seconds=approval_timeout,
            enable_slack=enable_slack,
            enable_webex=enable_webex,
            enable_teams=enable_teams,
            use_local_approval=use_local_approval,
            use_gui_approval=use_gui_approval,
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

