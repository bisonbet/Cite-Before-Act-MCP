#!/usr/bin/env python3
"""Interactive setup script for Cite-Before-Act MCP.

This script guides you through the complete setup process:
1. Creates virtual environment
2. Installs dependencies
3. Configures Slack integration (optional)
4. Sets up ngrok for webhooks (optional)
5. Generates Claude Desktop configuration
6. Creates startup scripts

Run: python3 setup_wizard.py
"""

import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict, Any


class Colors:
    """Terminal colors for better UX."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(70)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}\n")


def print_step(step: int, total: int, text: str) -> None:
    """Print a step indicator."""
    print(f"{Colors.CYAN}[Step {step}/{total}]{Colors.END} {Colors.BOLD}{text}{Colors.END}")


def print_success(text: str) -> None:
    """Print a success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_warning(text: str) -> None:
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")


def print_error(text: str) -> None:
    """Print an error message."""
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def prompt(question: str, default: Optional[str] = None) -> str:
    """Prompt user for input."""
    if default:
        question = f"{question} [{default}]: "
    else:
        question = f"{question}: "

    response = input(f"{Colors.CYAN}{question}{Colors.END}").strip()
    return response if response else (default or "")


def prompt_yes_no(question: str, default: bool = False) -> bool:
    """Prompt user for yes/no answer."""
    default_str = "Y/n" if default else "y/N"
    response = prompt(f"{question} ({default_str})", "").lower()

    if not response:
        return default
    return response in ['y', 'yes']


def run_command(cmd: list, cwd: Optional[Path] = None, check: bool = True) -> subprocess.CompletedProcess:
    """Run a command and return result."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=check
        )
        return result
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed: {' '.join(cmd)}")
        print_error(f"Error: {e.stderr}")
        raise


def find_python_installations() -> list[tuple[str, tuple[int, int, int]]]:
    """Find all available Python installations in PATH.

    Returns:
        List of tuples (python_path, (major, minor, micro))
    """
    python_versions = []

    # Common Python executable names to check
    python_names = [
        "python3.13", "python3.12", "python3.11", "python3.10",
        "python3", "python"
    ]

    checked_paths = set()  # Avoid duplicates

    for name in python_names:
        try:
            # Use 'which' to find the executable
            result = run_command(["which", name], check=False)
            if result.returncode == 0:
                python_path = result.stdout.strip()

                # Skip if we've already checked this path (symlinks)
                if python_path in checked_paths:
                    continue
                checked_paths.add(python_path)

                # Get version
                version_result = run_command([python_path, "--version"], check=False)
                if version_result.returncode == 0:
                    # Parse version string like "Python 3.12.0"
                    version_str = version_result.stdout.strip()
                    if version_str.startswith("Python "):
                        version_parts = version_str.split()[1].split(".")
                        if len(version_parts) >= 2:
                            major = int(version_parts[0])
                            minor = int(version_parts[1])
                            micro = int(version_parts[2]) if len(version_parts) > 2 else 0

                            # Only include Python 3.10+
                            if major >= 3 and minor >= 10:
                                python_versions.append((python_path, (major, minor, micro)))
        except Exception:
            continue

    # Sort by version (newest first)
    python_versions.sort(key=lambda x: x[1], reverse=True)

    return python_versions


def select_python_version() -> Optional[str]:
    """Let user select which Python version to use.

    Returns:
        Path to selected Python executable, or None if none available
    """
    pythons = find_python_installations()

    if not pythons:
        print_error("No Python 3.10+ installations found in PATH")
        print("\nSearched for: python3.13, python3.12, python3.11, python3.10, python3, python")
        print("Please install Python 3.10 or higher from: https://www.python.org/downloads/")
        return None

    # If running script with current Python and it's valid, prefer that
    current_python = sys.executable
    current_version = sys.version_info
    if current_version.major >= 3 and current_version.minor >= 10:
        # Check if current python is in our list
        for path, version in pythons:
            if path == current_python:
                print_success(f"Using current Python: {path} (v{version[0]}.{version[1]}.{version[2]})")
                return path

    # Show available options
    print(f"\n{Colors.CYAN}Available Python installations:{Colors.END}")
    for i, (path, version) in enumerate(pythons, 1):
        print(f"  {i}. Python {version[0]}.{version[1]}.{version[2]} - {path}")

    # Let user choose
    if len(pythons) == 1:
        if prompt_yes_no(f"\nUse Python {pythons[0][1][0]}.{pythons[0][1][1]}.{pythons[0][1][2]}?", default=True):
            selected = pythons[0][0]
            print_success(f"Selected: {selected}")
            return selected
        else:
            print_error("Setup cancelled - no Python version selected")
            return None
    else:
        default_choice = "1"
        choice = prompt(f"\nSelect Python version (1-{len(pythons)})", default_choice)

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(pythons):
                selected = pythons[idx][0]
                version = pythons[idx][1]
                print_success(f"Selected: Python {version[0]}.{version[1]}.{version[2]} - {selected}")
                return selected
            else:
                print_error(f"Invalid choice: {choice}")
                return None
        except ValueError:
            print_error(f"Invalid choice: {choice}")
            return None


def check_node_installed() -> bool:
    """Check if Node.js is installed."""
    try:
        result = run_command(["node", "--version"], check=False)
        if result.returncode == 0:
            version = result.stdout.strip()
            print_success(f"Node.js {version} detected")
            return True
    except FileNotFoundError:
        pass

    print_warning("Node.js not found (required for upstream MCP servers)")
    return False


def check_ngrok_installed() -> bool:
    """Check if ngrok is installed."""
    try:
        result = run_command(["ngrok", "version"], check=False)
        if result.returncode == 0:
            version = result.stdout.strip()
            print_success(f"ngrok {version} detected")
            return True
    except FileNotFoundError:
        pass

    print_warning("ngrok not installed")
    return False


def create_venv(project_dir: Path, python_exe: str) -> Path:
    """Create virtual environment.

    Args:
        project_dir: Project directory
        python_exe: Path to Python executable to use

    Returns:
        Path to venv directory
    """
    venv_dir = project_dir / ".venv"

    if venv_dir.exists():
        if prompt_yes_no(f"Virtual environment already exists at {venv_dir}. Recreate?", default=False):
            import shutil
            shutil.rmtree(venv_dir)
        else:
            print_success(f"Using existing virtual environment: {venv_dir}")
            return venv_dir

    print(f"Creating virtual environment with {python_exe}...")
    run_command([python_exe, "-m", "venv", str(venv_dir)])
    print_success(f"Virtual environment created: {venv_dir}")
    return venv_dir


def get_venv_python(venv_dir: Path) -> Path:
    """Get path to Python in virtual environment."""
    if platform.system() == "Windows":
        return venv_dir / "Scripts" / "python.exe"
    else:
        return venv_dir / "bin" / "python"


def install_dependencies(venv_dir: Path, project_dir: Path) -> None:
    """Install project dependencies."""
    python_exe = get_venv_python(venv_dir)

    # Clean up any existing build artifacts to avoid conflicts
    # This is especially important when switching Python versions
    import shutil
    cleaned = []
    
    # Directories to exclude from cleanup (don't touch venv, git, etc.)
    exclude_dirs = {'.venv', '.git', '__pycache__', '.pytest_cache', '.mypy_cache', 'node_modules'}
    
    # Clean up .egg-info and .dist-info directories (recursively)
    # Track what we've cleaned to avoid duplicates
    cleaned_paths = set()
    
    for pattern in ['*.egg-info', '*.dist-info']:
        for item in project_dir.rglob(pattern):
            # Skip if in an excluded directory
            if any(excluded in item.parts for excluded in exclude_dirs):
                continue
                
            if item.is_dir() and item not in cleaned_paths:
                rel_path = item.relative_to(project_dir)
                print(f"Removing existing build artifact: {rel_path}")
                try:
                    shutil.rmtree(item, ignore_errors=True)
                    # Verify it's actually gone
                    if item.exists():
                        print_warning(f"Could not fully remove {rel_path}, trying again...")
                        import time
                        time.sleep(0.1)  # Brief pause
                        shutil.rmtree(item, ignore_errors=True)
                    cleaned.append(str(rel_path))
                    cleaned_paths.add(item)
                except Exception as e:
                    print_warning(f"Error removing {rel_path}: {e}")
    
    # Also clean up build/ and dist/ directories if they exist
    for dir_name in ['build', 'dist']:
        dir_path = project_dir / dir_name
        if dir_path.exists() and dir_path.is_dir():
            print(f"Removing existing build directory: {dir_name}")
            try:
                shutil.rmtree(dir_path, ignore_errors=True)
                cleaned.append(dir_name)
            except Exception as e:
                print_warning(f"Error removing {dir_name}: {e}")
    
    if cleaned:
        print_success(f"Cleaned up {len(cleaned)} build artifact(s)")
    else:
        print("No existing build artifacts found")

    print("Installing project dependencies...")
    run_command([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"])
    
    # Try to uninstall any existing installation first (ignore errors if not installed)
    # This helps when switching Python versions
    print("Checking for existing package installation...")
    uninstall_result = run_command(
        [str(python_exe), "-m", "pip", "uninstall", "-y", "cite-before-act-mcp"],
        check=False
    )
    if uninstall_result.returncode == 0:
        print_success("Removed existing package installation")
    
    # Final cleanup pass right before install (in case anything was created)
    # Only clean from project root, not from venv or other excluded dirs
    exclude_dirs = {'.venv', '.git', '__pycache__', '.pytest_cache', '.mypy_cache', 'node_modules'}
    for item in list(project_dir.rglob('*.egg-info')):
        # Skip if in an excluded directory
        if any(excluded in item.parts for excluded in exclude_dirs):
            continue
        if item.is_dir() and item.exists():
            print(f"Final cleanup: removing {item.relative_to(project_dir)}")
            shutil.rmtree(item, ignore_errors=True)
    
    # Also do a targeted cleanup of any .egg-info in the project root specifically
    # (these are the most likely culprits)
    for item in project_dir.iterdir():
        if item.is_dir() and item.name.endswith('.egg-info'):
            print(f"Removing root-level .egg-info: {item.name}")
            shutil.rmtree(item, ignore_errors=True)
    
    # Diagnostic: List any remaining .egg-info directories (should be none)
    remaining_egg_info = []
    for item in project_dir.rglob('*.egg-info'):
        if any(excluded in item.parts for excluded in exclude_dirs):
            continue
        if item.is_dir() and item.exists():
            remaining_egg_info.append(item.relative_to(project_dir))
    
    if remaining_egg_info:
        print_warning(f"Found {len(remaining_egg_info)} remaining .egg-info directories:")
        for path in remaining_egg_info:
            print_warning(f"  - {path}")
        print_warning("Attempting to remove them...")
        for path in remaining_egg_info:
            full_path = project_dir / path
            shutil.rmtree(full_path, ignore_errors=True)
    
    # Install in editable mode
    # Note: setup_wizard.py is renamed from setup.py to avoid setuptools confusion
    # setuptools would try to use both setup.py and pyproject.toml, causing multiple .egg-info
    print("Installing package in editable mode...")
    run_command(
        [str(python_exe), "-m", "pip", "install", "--use-pep517", "-e", "."],
        cwd=project_dir
    )

    print_success("Dependencies installed")


def configure_slack() -> Dict[str, Any]:
    """Configure Slack integration."""
    config = {}

    print("\n" + "─" * 70)
    print("Slack Configuration")
    print("─" * 70)

    if not prompt_yes_no("Do you want to enable Slack integration?", default=False):
        return {"enabled": False}

    config["enabled"] = True

    print("\n📱 To get your Slack bot token:")
    print("1. Go to: https://api.slack.com/apps")
    print("2. Create a new app or select existing app")
    print("3. Go to: OAuth & Permissions")
    print("4. Add OAuth scopes: chat:write, channels:read, groups:read")
    print("5. Install app to workspace")
    print("6. Copy the 'Bot User OAuth Token' (starts with xoxb-)")

    config["bot_token"] = prompt("\nSlack Bot Token (xoxb-...)")

    if not config["bot_token"].startswith("xoxb-"):
        print_warning("Token should start with 'xoxb-' - please verify")

    # Channel or DM
    if prompt_yes_no("\nSend approvals to a channel?", default=True):
        print("\nChannel format:")
        print("  - Public channels: #approvals (with #)")
        print("  - Private channels: approvals (without #, and invite bot: /invite @YourBot)")
        config["channel"] = prompt("Channel name")
        config["user_id"] = None
    else:
        print("\n👤 To get user ID for DMs:")
        print("1. In Slack, click on your profile")
        print("2. Click '...' → Copy member ID")
        config["user_id"] = prompt("User ID (U...)")
        config["channel"] = None

    # Webhook server
    if prompt_yes_no("\nEnable interactive Approve/Reject buttons?", default=True):
        config["webhook_enabled"] = True

        print("\n📝 To get your Slack signing secret:")
        print("1. Go to: https://api.slack.com/apps → Your App")
        print("2. Go to: Basic Information → App Credentials")
        print("3. Copy the 'Signing Secret'")

        config["signing_secret"] = prompt("\nSlack Signing Secret")

        # Ask about hosting
        print("\nWebhook Hosting:")
        print("1. Web Service (ngrok) - Easiest, great for development and small-scale production")
        print("2. Self-Hosted (cloud/VPS) - For larger deployments")

        hosting_choice = prompt("Choose hosting method (1/2)", "1")
        config["webhook_hosting"] = "ngrok" if hosting_choice == "1" else "self-hosted"
    else:
        config["webhook_enabled"] = False

    return config


def configure_webex() -> Dict[str, Any]:
    """Configure Webex integration."""
    config = {}

    print("\n" + "─" * 70)
    print("Webex Configuration")
    print("─" * 70)

    if not prompt_yes_no("Do you want to enable Webex integration?", default=False):
        return {"enabled": False}

    config["enabled"] = True

    print("\n📱 To get your Webex bot token:")
    print("1. Go to: https://developer.webex.com/my-apps")
    print("2. Create a new app → Create a Bot")
    print("3. Fill in bot details (name, username, icon)")
    print("4. Copy the 'Bot's Access Token' (starts with Y2lzY29...)")
    print("   ⚠️  WARNING: Token is only shown once! Save it immediately!")

    config["bot_token"] = prompt("\nWebex Bot Token")

    # Room or Direct Message
    if prompt_yes_no("\nSend approvals to a Webex space/room?", default=True):
        print("\n📝 To get room ID:")
        print("1. Add your bot to a Webex space")
        print("2. Use the Webex API to list rooms:")
        print("   curl -X GET https://webexapis.com/v1/rooms \\")
        print("     -H 'Authorization: Bearer YOUR_TOKEN'")
        print("3. Or use Python: api.rooms.list()")
        config["room_id"] = prompt("Room ID")
        config["person_email"] = None
    else:
        print("\n👤 To send direct messages:")
        print("1. Get the person's Webex email address")
        print("2. Note: Person must have interacted with bot first")
        config["person_email"] = prompt("Person Email")
        config["room_id"] = None

    # Webhook server (always needed for Webex buttons)
    print("\n📌 Webex requires a webhook to receive button click events.")
    print("   You'll need to:")
    print("   1. Run the unified webhook server")
    print("   2. Create a webhook for attachmentActions")
    print("   3. Update webhook URL when ngrok restarts (or use stable domain)")
    config["webhook_enabled"] = True

    return config


def configure_teams() -> Dict[str, Any]:
    """Configure Microsoft Teams integration."""
    config = {}

    print("\n" + "─" * 70)
    print("Microsoft Teams Configuration")
    print("─" * 70)

    if not prompt_yes_no("Do you want to enable Microsoft Teams integration?", default=False):
        return {"enabled": False}

    config["enabled"] = True

    print("\n📱 Microsoft Teams setup is more complex than Slack/Webex:")
    print("1. Requires Azure Bot Service")
    print("2. Requires App Registration in Microsoft Entra ID")
    print("3. Requires Bot Framework SDK")
    print("\n📚 For detailed setup instructions, see: docs/TEAMS_SETUP.md")

    print("\n🔑 To get your Teams credentials:")
    print("1. Go to Azure Portal: https://portal.azure.com")
    print("2. Create App Registration in Microsoft Entra ID")
    print("   (Note: Microsoft Entra ID is the new name for Azure Active Directory)")
    print("3. Generate client secret (save immediately!)")
    print("4. Create Azure Bot resource")
    print("5. Configure messaging endpoint (your webhook URL)")

    config["app_id"] = prompt("\nTeams App ID (Application/Client ID)")
    config["app_password"] = prompt("Teams App Password (Client Secret)")

    # Optional: Service URL and conversation reference
    print("\n📝 Optional settings:")
    service_url = prompt("Teams Service URL (press Enter for default)", "https://smba.trafficmanager.net/amer/")
    if service_url:
        config["service_url"] = service_url

    # Webhook server (always needed for Teams)
    print("\n�� Teams requires a webhook endpoint at /api/messages")
    print("   The bot will receive all messages and invoke activities here.")
    config["webhook_enabled"] = True

    return config


def configure_ngrok(slack_config: Dict[str, Any], webex_config: Dict[str, Any], teams_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Configure ngrok for webhooks.

    Args:
        slack_config: Slack configuration dict
        webex_config: Webex configuration dict
        teams_config: Teams configuration dict

    Returns:
        ngrok configuration dict or None if not needed
    """
    # Check if any platform needs webhooks
    needs_webhook = (
        slack_config.get("webhook_enabled") or
        webex_config.get("webhook_enabled") or
        teams_config.get("webhook_enabled")
    )

    if not needs_webhook:
        return None

    # For Slack, check if using ngrok (vs self-hosted)
    # For Webex and Teams, webhooks are always needed
    slack_uses_ngrok = slack_config.get("webhook_enabled") and slack_config.get("webhook_hosting") == "ngrok"

    # If Slack is enabled but using self-hosted, and no other platforms need webhooks, skip ngrok
    if slack_config.get("webhook_enabled") and not slack_uses_ngrok:
        if not (webex_config.get("enabled") or teams_config.get("enabled")):
            return None

    print("\n" + "─" * 70)
    print("ngrok Configuration")
    print("─" * 70)

    if not check_ngrok_installed():
        print("\n📥 Install ngrok:")
        print("1. Download from: https://ngrok.com/download")
        print("2. Or install via package manager:")
        print("   - macOS: brew install ngrok")
        print("   - Windows: choco install ngrok")
        print("   - Linux: snap install ngrok")

        if not prompt_yes_no("\nHave you installed ngrok?", default=False):
            print_warning("Skipping ngrok configuration. You can set it up later.")
            return None

    config = {}

    # Ask for authtoken (optional but recommended)
    if prompt_yes_no("\nDo you have an ngrok account/authtoken?", default=False):
        print("\n🔑 To get your authtoken:")
        print("1. Sign up at: https://ngrok.com/signup")
        print("2. Go to: https://dashboard.ngrok.com/get-started/your-authtoken")

        authtoken = prompt("ngrok authtoken (optional - press Enter to skip)", "")
        if authtoken:
            config["authtoken"] = authtoken
            # Configure authtoken
            try:
                run_command(["ngrok", "config", "add-authtoken", authtoken])
                print_success("ngrok authtoken configured")
            except Exception as e:
                print_warning(f"Could not configure authtoken: {e}")

    config["port"] = prompt("Webhook server port", "3000")

    return config


def configure_upstream() -> Dict[str, Any]:
    """Configure upstream MCP server."""
    print("\n" + "─" * 70)
    print("Upstream MCP Server Configuration")
    print("─" * 70)

    print("\nThe upstream server is the MCP server you want to wrap with approval requirements.")
    print("\nCommon examples:")
    print("1. Filesystem Server (official MCP filesystem server)")
    print("2. GitHub MCP Server (GitHub's official MCP server)")
    print("3. Custom Server (your own MCP server)")

    choice = prompt("Choose option (1/2/3)", "1")

    if choice == "1":
        # Filesystem server
        print("\nFilesystem Server Setup:")
        print("This will use: npx @modelcontextprotocol/server-filesystem")

        # Get or create test directory
        default_dir = str(Path.home() / "mcp-test-workspace")
        workspace_dir = prompt(f"\nWorkspace directory path", default_dir)

        workspace_path = Path(workspace_dir).expanduser().resolve()
        if not workspace_path.exists():
            if prompt_yes_no(f"Directory doesn't exist. Create {workspace_path}?", default=True):
                workspace_path.mkdir(parents=True, exist_ok=True)
                print_success(f"Created directory: {workspace_path}")

        return {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", str(workspace_path)],
            "transport": "stdio"
        }
    elif choice == "2":
        # GitHub MCP server (local only - remote requires OAuth which is complex)
        print("\n" + "─" * 70)
        print("GitHub MCP Server Setup (Local)")
        print("─" * 70)
        print("\nThis will use a local GitHub MCP server binary.")
        print("\nNote: The remote GitHub MCP server requires OAuth authentication,")
        print("which is complex to set up. We recommend using the local server.")
        print("\n📦 Installation options:")
        print("  1. Docker (easiest, cross-platform):")
        print("     docker run -i --rm ghcr.io/github/github-mcp-server")
        print("  2. Download binary from: https://github.com/github/github-mcp-server/releases")
        print("  3. Build from source with Go: go build ./cmd/github-mcp-server")
        print("\nYou'll also need:")
        print("  • GitHub Personal Access Token (create at https://github.com/settings/tokens)")

        # Check if github-mcp-server is in PATH
        import shutil
        github_mcp_path = shutil.which("github-mcp-server")
        docker_path = shutil.which("docker")

        if github_mcp_path:
            print_success(f"Found github-mcp-server at: {github_mcp_path}")
            default_command = "github-mcp-server"
        elif docker_path:
            print_success(f"Found docker at: {docker_path}")
            print("Recommend using Docker for easiest setup")
            default_command = "docker"
        else:
            print_warning("Neither github-mcp-server nor docker found in PATH")
            default_command = "github-mcp-server"

        command_choice = prompt(f"Command to use (github-mcp-server/docker/custom path)", default_command)

        if command_choice == "docker":
            command = "docker"
            args = ["run", "-i", "--rm", "ghcr.io/github/github-mcp-server"]
        elif command_choice == "github-mcp-server":
            command = "github-mcp-server"
            args = []
        else:
            # Custom path
            command = command_choice
            args = []

        # Get GitHub token
        print("\n📝 GitHub Personal Access Token:")
        print("Required scopes: repo, workflow, write:packages, delete:packages, admin:org, etc.")
        print("Or use minimal scopes needed for your use case")
        token = prompt("GitHub Personal Access Token", "")

        if not token:
            print_warning("No token provided. You'll need to set GITHUB_PERSONAL_ACCESS_TOKEN in your .env file")

        # Optional: additional flags (only if not using docker)
        if command != "docker":
            print("\nOptional GitHub MCP Server flags:")
            print("Common options: --read-only, --lockdown-mode, --dynamic-toolsets")
            additional_args_str = prompt("Additional arguments (comma-separated, or press Enter for none)", "")
            if additional_args_str:
                args.extend([arg.strip() for arg in additional_args_str.split(",")])

        config = {
            "command": command,
            "args": args,
            "transport": "stdio",
        }

        # Only add token to config if provided (don't add empty string)
        if token:
            config["github_token"] = token

        return config
    else:
        # Custom server
        print("\nCustom Server Setup:")
        command = prompt("Command to run server (e.g., python, node)")
        args_str = prompt("Arguments (comma-separated, e.g., -m,myserver,--port,8000)")
        args = [arg.strip() for arg in args_str.split(",")] if args_str else []
        transport = prompt("Transport type (stdio/http/sse)", "stdio")

        config = {
            "command": command,
            "args": args,
            "transport": transport
        }

        if transport in ["http", "sse"]:
            url = prompt("Upstream server URL")
            config["url"] = url

        return config


def generate_env_file(project_dir: Path, slack_config: Dict[str, Any], webex_config: Dict[str, Any], teams_config: Dict[str, Any], upstream_config: Dict[str, Any]) -> None:
    """Generate .env file with secrets and global settings.

    The .env file contains:
    - Secrets (GITHUB_PERSONAL_ACCESS_TOKEN, SLACK_BOT_TOKEN, WEBEX_BOT_TOKEN, TEAMS_APP_ID, etc.)
    - Global settings that apply to ALL MCP servers (ENABLE_SLACK, ENABLE_WEBEX, ENABLE_TEAMS, etc.)
    - Global detection defaults (DETECTION_ENABLE_CONVENTION, DETECTION_ENABLE_METADATA)

    Server-specific config (UPSTREAM_COMMAND, UPSTREAM_ARGS, etc.) goes in
    mcpServers.env in Claude Desktop config, NOT in this .env file.

    Args:
        project_dir: Project directory path
        slack_config: Slack configuration dict
        webex_config: Webex configuration dict
        teams_config: Teams configuration dict
        upstream_config: Upstream server configuration dict

    If .env exists and has a GitHub token set, we'll append the token if needed.
    If .env doesn't exist or you confirm overwrite, regenerates the entire file.
    """
    env_path = project_dir / ".env"

    # Check if .env exists and has required tokens
    if env_path.exists():
        # Check if GitHub token is already set
        has_github_token = False
        try:
            with open(env_path, "r") as f:
                content = f.read()
                # Check if GITHUB_PERSONAL_ACCESS_TOKEN has a value (not empty)
                for line in content.split("\n"):
                    if line.startswith("GITHUB_PERSONAL_ACCESS_TOKEN=") and "=" in line:
                        value = line.split("=", 1)[1].strip()
                        if value:  # Has a non-empty value
                            has_github_token = True
                            break
        except Exception:
            pass

        # If adding GitHub server and token not in .env, append it
        if upstream_config.get("github_token") is not None and not has_github_token:
            print(f"\nAdding GitHub token to existing .env file...")
            try:
                with open(env_path, "a") as f:
                    f.write("\n# -----------------------------------------------------------------------------\n")
                    f.write("# GitHub Configuration (Global)\n")
                    f.write("# -----------------------------------------------------------------------------\n")
                    f.write("# GitHub Personal Access Token (global secret)\n")
                    f.write("# Get from: https://github.com/settings/tokens\n")
                    f.write("# Required scopes: repo, workflow, write:packages, delete:packages, admin:org\n")
                    if upstream_config.get("github_token"):
                        f.write(f"GITHUB_PERSONAL_ACCESS_TOKEN={upstream_config['github_token']}\n")
                    else:
                        f.write("GITHUB_PERSONAL_ACCESS_TOKEN=\n")
                print_success(f"Added GitHub configuration to .env file: {env_path}")
                return
            except Exception as e:
                print_error(f"Could not append to .env: {e}")

        # Otherwise ask if they want to overwrite
        if not prompt_yes_no(f"\n.env file already exists. Regenerate entire file?", default=False):
            print_warning("Keeping existing .env file. You may need to manually add configuration.")
            return

    print("\nGenerating .env file...")

    lines = [
        "# =============================================================================",
        "# Cite-Before-Act MCP - Global Configuration and Secrets",
        "# =============================================================================",
        "# Generated by setup_wizard.py",
        "#",
        "# This file contains:",
        "# - Secrets (tokens, passwords) - NEVER commit to git!",
        "# - Global settings that apply to ALL MCP servers",
        "#",
        "# Server-specific config (UPSTREAM_COMMAND, UPSTREAM_ARGS, etc.) is in",
        "# Claude Desktop's mcpServers config, NOT here.",
        "#",
        "# Environment variable precedence:",
        "# 1. mcpServers.env (highest priority) - per-server overrides",
        "# 2. This .env file (lower priority) - global defaults",
        "# =============================================================================",
        "",
        "# -----------------------------------------------------------------------------",
        "# Secrets (NEVER commit these to git!)",
        "# -----------------------------------------------------------------------------",
    ]

    # Add GitHub token if provided
    if upstream_config.get("github_token") is not None:
        # GitHub token was requested (either provided or skipped)
        lines.extend([
            "",
            "# GitHub Personal Access Token (global secret)",
            "# Get from: https://github.com/settings/tokens",
            "# Required scopes: repo, workflow, write:packages, delete:packages, admin:org",
        ])

        if upstream_config.get("github_token"):
            # Token was provided
            lines.append(f"GITHUB_PERSONAL_ACCESS_TOKEN={upstream_config['github_token']}")
        else:
            # Token not provided - add placeholder with instructions
            lines.append("GITHUB_PERSONAL_ACCESS_TOKEN=")

    # Add Slack configuration if enabled
    if slack_config["enabled"]:
        lines.extend([
            "",
            "# -----------------------------------------------------------------------------",
            "# Slack Configuration (Global)",
            "# -----------------------------------------------------------------------------",
            f"SLACK_BOT_TOKEN={slack_config['bot_token']}",
            f"ENABLE_SLACK=true",
        ])

        if slack_config.get("channel"):
            lines.append(f"SLACK_CHANNEL={slack_config['channel']}")
        elif slack_config.get("user_id"):
            lines.append(f"SLACK_USER_ID={slack_config['user_id']}")

        if slack_config.get("webhook_enabled"):
            lines.extend([
                "",
                "# Slack Webhook Configuration",
                f"SLACK_SIGNING_SECRET={slack_config['signing_secret']}",
            ])

    # Add Webex configuration if enabled
    if webex_config["enabled"]:
        lines.extend([
            "",
            "# -----------------------------------------------------------------------------",
            "# Webex Configuration (Global)",
            "# -----------------------------------------------------------------------------",
            f"WEBEX_BOT_TOKEN={webex_config['bot_token']}",
            f"ENABLE_WEBEX=true",
        ])

        if webex_config.get("room_id"):
            lines.append(f"WEBEX_ROOM_ID={webex_config['room_id']}")
        elif webex_config.get("person_email"):
            lines.append(f"WEBEX_PERSON_EMAIL={webex_config['person_email']}")

    # Add Teams configuration if enabled
    if teams_config["enabled"]:
        lines.extend([
            "",
            "# -----------------------------------------------------------------------------",
            "# Microsoft Teams Configuration (Global)",
            "# -----------------------------------------------------------------------------",
            f"TEAMS_APP_ID={teams_config['app_id']}",
            f"TEAMS_APP_PASSWORD={teams_config['app_password']}",
            f"ENABLE_TEAMS=true",
        ])

        if teams_config.get("service_url"):
            lines.append(f"TEAMS_SERVICE_URL={teams_config['service_url']}")

    # Webhook hosting configuration (applies to all platforms)
    any_webhook = (slack_config.get("webhook_enabled") or
                   webex_config.get("webhook_enabled") or
                   teams_config.get("webhook_enabled"))

    if any_webhook:
        lines.extend([
            "",
            "# -----------------------------------------------------------------------------",
            "# Webhook Server Configuration",
            "# -----------------------------------------------------------------------------",
        ])

        # Determine security mode based on Slack hosting choice (if applicable)
        if slack_config.get("webhook_enabled"):
            if slack_config.get("webhook_hosting") == "self-hosted":
                lines.append("SECURITY_MODE=production")
                lines.append("HOST=0.0.0.0  # Listen on all interfaces for production")
            else:
                lines.append("SECURITY_MODE=local")
                lines.append("HOST=127.0.0.1  # Only localhost when using ngrok")
        else:
            # Default for Webex/Teams only
            lines.append("SECURITY_MODE=local")
            lines.append("HOST=127.0.0.1  # Only localhost when using ngrok")

    # Global approval settings
    lines.extend([
        "",
        "# -----------------------------------------------------------------------------",
        "# Global Approval Settings",
        "# -----------------------------------------------------------------------------",
        "# These apply to ALL MCP servers. You can override per-server by adding",
        "# these variables to the specific server's env in Claude Desktop config.",
        "",
        "APPROVAL_TIMEOUT_SECONDS=300",
        "USE_LOCAL_APPROVAL=true",
    ])

    # Set USE_GUI_APPROVAL based on any platform being enabled
    if any([slack_config.get("enabled"), webex_config.get("enabled"), teams_config.get("enabled")]):
        lines.append("USE_GUI_APPROVAL=false  # Disabled when any platform is enabled")
    else:
        lines.append("USE_GUI_APPROVAL=true   # Enabled when no platforms are enabled")

    # Global detection defaults
    lines.extend([
        "",
        "# -----------------------------------------------------------------------------",
        "# Global Detection Defaults",
        "# -----------------------------------------------------------------------------",
        "# These are global defaults. Per-server DETECTION_ALLOWLIST and",
        "# DETECTION_BLOCKLIST are set in Claude Desktop's mcpServers config.",
        "",
        "DETECTION_ENABLE_CONVENTION=true",
        "DETECTION_ENABLE_METADATA=true",
        "",
    ])

    with open(env_path, "w") as f:
        f.write("\n".join(lines))

    print_success(f"Created .env file: {env_path}")


def generate_claude_config(project_dir: Path, venv_dir: Path, slack_config: Dict[str, Any], upstream_config: Dict[str, Any]) -> Dict[str, Any]:
    """Generate Claude Desktop MCP configuration.

    This config includes:
    - Server-specific upstream configuration (command, args, transport, URL)
    - Optional per-server detection overrides (allowlist/blocklist)

    Global settings (ENABLE_SLACK, USE_LOCAL_APPROVAL, etc.) and secrets
    (GITHUB_PERSONAL_ACCESS_TOKEN, SLACK_BOT_TOKEN) are loaded from .env file.

    Environment variable precedence:
    1. mcpServers.env (this config) - highest priority, server-specific
    2. .env file - lower priority, global defaults and secrets

    This allows per-server overrides while .env provides global configuration.
    """
    python_exe = get_venv_python(venv_dir)

    # Set defaults based on upstream server type
    is_github = (
        upstream_config.get("command") == "github-mcp-server"
        or "github" in upstream_config.get("command", "").lower()
        or upstream_config.get("transport") == "http" and "githubcopilot.com" in upstream_config.get("url", "")
    )

    # Only include upstream-server-specific configuration
    # Global settings (Slack, approvals, etc.) come from .env file
    env = {
        # Optional per-server detection overrides
        # These override global defaults from .env if needed
        "DETECTION_ALLOWLIST": "" if is_github else "write_file,edit_file,create_directory,move_file",
        "DETECTION_BLOCKLIST": "read_file,get_file,list_files,search_code,get_issue,list_issues,get_pull_request,list_pull_requests,search_repositories,get_repository,list_repositories,get_user,list_users,search_users" if is_github else "read_text_file,read_media_file,list_directory,get_file_info",
    }

    # Handle different transport types - this is server-specific config
    if upstream_config.get("transport") == "http":
        # HTTP transport (remote server)
        env["UPSTREAM_URL"] = upstream_config["url"]
        env["UPSTREAM_TRANSPORT"] = "http"
        # Note: Token is read from .env file (GITHUB_PERSONAL_ACCESS_TOKEN or UPSTREAM_AUTH_TOKEN)
        # config/settings.py automatically loads it and adds Authorization header
    else:
        # stdio transport (local server)
        env["UPSTREAM_COMMAND"] = upstream_config["command"]
        env["UPSTREAM_ARGS"] = ",".join(upstream_config["args"])
        env["UPSTREAM_TRANSPORT"] = upstream_config["transport"]
        # Note: Token is read from .env file (GITHUB_PERSONAL_ACCESS_TOKEN)
        # config/settings.py automatically loads it and passes to upstream server

    # Note: Global settings like ENABLE_SLACK, SLACK_CHANNEL, USE_LOCAL_APPROVAL,
    # USE_GUI_APPROVAL, APPROVAL_TIMEOUT_SECONDS are loaded from .env file.
    # They apply to all servers and can be overridden per-server if needed by
    # adding them to this env dict.

    config = {
        "cite-before-act": {
            "command": str(python_exe),
            "args": ["-m", "server.main", "--transport", "stdio"],
            "env": env
        }
    }

    return config


def save_claude_config(config: Dict[str, Any], project_dir: Path) -> None:
    """Save Claude Desktop configuration to file.
    
    Args:
        config: Configuration dict. If it already has "mcpServers" key, use as-is.
                Otherwise, treat the dict as mcpServers content.
        project_dir: Project directory path
    """
    config_path = project_dir / "claude_desktop_config_generated.json"

    # If config already has mcpServers key, use it directly
    if "mcpServers" in config:
        output_config = config
    else:
        # Otherwise, wrap it
        output_config = {"mcpServers": config}
    
    # Note: We no longer use Claude Desktop's "inputs" feature for tokens.
    # All secrets are stored in .env file and loaded by python-dotenv.

    with open(config_path, "w") as f:
        json.dump(output_config, f, indent=2)

    print_success(f"Saved configuration: {config_path}")


def create_ngrok_policy(project_dir: Path, signing_secret: str) -> Path:
    """Create ngrok traffic policy file.
    
    Note: webhook-verification may require ngrok Pro/Enterprise plan.
    If you get ERR_NGROK_2201, use application-level verification instead
    by setting SECURITY_MODE=production in your .env file.
    """
    policy_path = project_dir / "ngrok-slack-policy.yml"

    content = f"""# ngrok Traffic Policy for Slack Webhook Verification
# Generated by setup_wizard.py
#
# This policy validates Slack request signatures at the tunnel level
# before forwarding requests to your application.
#
# Learn more: https://ngrok.com/docs/integrations/webhooks/slack-webhooks
# Action reference: https://ngrok.com/docs/traffic-policy/actions/verify-webhook

on_http_request:
  - actions:
      - type: "verify-webhook"
        config:
          provider: "slack"
          secret: "{signing_secret}"
"""

    with open(policy_path, "w") as f:
        f.write(content)

    # Add to .gitignore if not already there
    gitignore_path = project_dir / ".gitignore"
    if gitignore_path.exists():
        with open(gitignore_path, "r") as f:
            content = f.read()

        if "ngrok-slack-policy.yml" not in content:
            with open(gitignore_path, "a") as f:
                f.write("\n# ngrok config with secrets\nngrok-slack-policy.yml\n")

    print_success(f"Created ngrok policy: {policy_path}")
    print_warning("Note: This file contains secrets - it has been added to .gitignore")

    return policy_path


def create_startup_scripts(project_dir: Path, venv_dir: Path, slack_config: Dict[str, Any], webex_config: Dict[str, Any], teams_config: Dict[str, Any], ngrok_config: Optional[Dict[str, Any]]) -> None:
    """Create convenience startup scripts.

    Args:
        project_dir: Project directory path
        venv_dir: Virtual environment directory path
        slack_config: Slack configuration dict
        webex_config: Webex configuration dict
        teams_config: Teams configuration dict
        ngrok_config: ngrok configuration dict (if applicable)
    """
    # Check if any platform needs webhooks
    any_webhook = (slack_config.get("webhook_enabled") or
                   webex_config.get("webhook_enabled") or
                   teams_config.get("webhook_enabled"))

    if not any_webhook:
        return

    print("\nCreating startup scripts...")

    python_exe = get_venv_python(venv_dir)

    # Determine which webhook server to use
    # Use unified server if multiple platforms enabled OR if Webex/Teams is enabled
    enabled_platforms = sum([
        slack_config.get("enabled", False),
        webex_config.get("enabled", False),
        teams_config.get("enabled", False)
    ])

    use_unified = (enabled_platforms > 1 or
                   webex_config.get("enabled") or
                   teams_config.get("enabled"))

    webhook_script = "examples/unified_webhook_server.py" if use_unified else "examples/slack_webhook_server.py"

    if platform.system() == "Windows":
        # Windows batch file
        script_path = project_dir / "start_webhook.bat"
        env_file = project_dir / ".env"
        content = f"""@echo off
REM Start Slack Webhook Server
REM Generated by setup_wizard.py

REM Load environment variables from .env if it exists
if exist "{env_file}" (
    for /f "usebackq tokens=1,* delims==" %%a in ("{env_file}") do (
        if not "%%a"=="" if not "%%a"=="#" (
            set "%%a=%%b"
        )
    )
)

echo Starting Webhook Server...
"{python_exe}" {webhook_script.replace("/", "\\")}
"""
        if ngrok_config:
            ngrok_script = project_dir / "start_ngrok.bat"
            port = ngrok_config.get("port", "3000")
            policy_file = project_dir / "ngrok-slack-policy.yml"
            ngrok_content = f"""@echo off
REM Start ngrok tunnel and automatically configure webhooks
REM Generated by setup_wizard.py
REM
REM This script:
REM - Starts ngrok on port {port}
REM - Automatically gets the ngrok URL
REM - Creates/updates Webex webhooks if ENABLE_WEBEX=true
REM - Shows Teams webhook URL for manual Azure Bot configuration
REM
REM NOTE: For Slack webhook verification:
REM - If you get ERR_NGROK_2201, check that your ngrok version supports verify-webhook.
REM - Fallback: Use application-level verification instead:
REM   1. Edit .env and set: SECURITY_MODE=production
REM   2. The webhook server will handle verification in application code

cd /d "%~dp0"

REM Use the Python script that auto-configures webhooks
python scripts\\start_ngrok_with_webhooks.py
"""
            with open(ngrok_script, "w") as f:
                f.write(ngrok_content)
            print_success(f"Created: {ngrok_script}")
            with open(ngrok_script, "w") as f:
                f.write(ngrok_content)
            print_success(f"Created: {ngrok_script}")
    else:
        # Unix shell script
        script_path = project_dir / "start_webhook.sh"
        env_file = project_dir / ".env"
        content = f"""#!/bin/bash
# Start Slack Webhook Server
# Generated by setup_wizard.py

# Load environment variables from .env if it exists
if [ -f "{env_file}" ]; then
    set -a
    source "{env_file}"
    set +a
fi

echo "Starting Webhook Server..."
"{python_exe}" {webhook_script}
"""
        with open(script_path, "w") as f:
            f.write(content)
        script_path.chmod(0o755)  # Make executable

        if ngrok_config:
            ngrok_script = project_dir / "start_ngrok.sh"
            port = ngrok_config.get("port", "3000")
            policy_file = project_dir / "ngrok-slack-policy.yml"
            
            # Use the new script that auto-configures webhooks
            ngrok_content = f"""#!/bin/bash
# Start ngrok tunnel and automatically configure webhooks
# Generated by setup_wizard.py
#
# This script:
# - Starts ngrok on port {port}
# - Automatically gets the ngrok URL
# - Creates/updates Webex webhooks if ENABLE_WEBEX=true
# - Shows Teams webhook URL for manual Azure Bot configuration
#
# NOTE: For Slack webhook verification:
# - If you get ERR_NGROK_2201, check that your ngrok version supports verify-webhook.
# - Fallback: Use application-level verification instead:
#   1. Edit .env and set: SECURITY_MODE=production
#   2. The webhook server will handle verification in application code

cd "$(dirname "$0")"

# Use the Python script that auto-configures webhooks
python3 scripts/start_ngrok_with_webhooks.py
"""
            with open(ngrok_script, "w") as f:
                f.write(ngrok_content)
            ngrok_script.chmod(0o755)  # Make executable
            print_success(f"Created: {ngrok_script}")

    with open(script_path, "w") as f:
        f.write(content)

    print_success(f"Created: {script_path}")


def print_final_instructions(project_dir: Path, slack_config: Dict[str, Any], webex_config: Dict[str, Any], teams_config: Dict[str, Any], ngrok_config: Optional[Dict[str, Any]], claude_config: Dict[str, Any]) -> None:
    """Print final setup instructions.

    Args:
        project_dir: Project directory path
        slack_config: Slack configuration dict
        webex_config: Webex configuration dict
        teams_config: Teams configuration dict
        ngrok_config: ngrok configuration dict (if applicable)
        claude_config: Claude Desktop configuration dict
    """
    print_header("🎉 Setup Complete!")

    print("📋 Next Steps:\n")

    # Claude Desktop configuration
    print(f"{Colors.BOLD}1. Configure Claude Desktop:{Colors.END}")
    print(f"   Copy the contents of: {Colors.CYAN}claude_desktop_config_generated.json{Colors.END}")
    print(f"   to your Claude Desktop config file:")

    system = platform.system()
    if system == "Darwin":
        config_path = "~/Library/Application Support/Claude/claude_desktop_config.json"
    elif system == "Windows":
        config_path = "%APPDATA%\\Claude\\claude_desktop_config.json"
    else:
        config_path = "~/.config/Claude/claude_desktop_config.json"

    print(f"   {Colors.YELLOW}{config_path}{Colors.END}")

    # Webhook setup for any enabled platform
    any_webhook = (slack_config.get("webhook_enabled") or
                   webex_config.get("webhook_enabled") or
                   teams_config.get("webhook_enabled"))

    if any_webhook:
        print(f"\n{Colors.BOLD}2. Start the Webhook Server:{Colors.END}")

        if platform.system() == "Windows":
            print(f"   {Colors.CYAN}start_webhook.bat{Colors.END}")
        else:
            print(f"   {Colors.CYAN}./start_webhook.sh{Colors.END}")

        if ngrok_config:
            print(f"\n{Colors.BOLD}3. Start ngrok (in another terminal):{Colors.END}")

            if platform.system() == "Windows":
                print(f"   {Colors.CYAN}start_ngrok.bat{Colors.END}")
            else:
                print(f"   {Colors.CYAN}./start_ngrok.sh{Colors.END}")

            print(f"\n{Colors.BOLD}4. Configure Platform Webhooks:{Colors.END}")

            if slack_config.get("webhook_enabled"):
                print(f"\n   {Colors.CYAN}Slack:{Colors.END}")
                print("   a. Copy the ngrok URL from the terminal")
                print("   b. Go to: https://api.slack.com/apps → Your App")
                print("   c. Go to: Interactivity & Shortcuts")
                print("   d. Set Request URL to: https://YOUR-NGROK-URL.ngrok.io/slack/interactive")
                print("   e. Save changes")

            if webex_config.get("webhook_enabled"):
                print(f"\n   {Colors.CYAN}Webex:{Colors.END}")
                print("   ✅ Webhook will be automatically configured when you run start_ngrok!")
                print("   The script will:")
                print("   - Get the ngrok URL automatically")
                print("   - Create/update the Webex webhook for attachmentActions")
                print("   - Show the webhook URL in the output")
                print("   Note: If ngrok restarts, just run start_ngrok again to update the webhook")

            if teams_config.get("webhook_enabled"):
                print(f"\n   {Colors.CYAN}Microsoft Teams:{Colors.END}")
                print("   a. Copy the ngrok URL from the terminal")
                print("   b. Go to Azure Portal → Your Bot → Configuration")
                print("   c. Set Messaging endpoint to: https://YOUR-NGROK-URL.ngrok.io/api/messages")
                print("   d. Save configuration")
        else:
            print(f"\n{Colors.BOLD}3. Deploy webhook server to your cloud/VPS{Colors.END}")
            print("   Ensure HTTPS is enabled (required by all platforms)")

    print(f"\n{Colors.BOLD}5. Restart Claude Desktop{Colors.END}")
    print("   Completely quit and reopen Claude Desktop")

    print(f"\n{Colors.BOLD}6. Test the Setup:{Colors.END}")
    print("   In Claude Desktop, try:")
    print(f"   {Colors.CYAN}\"Create a file called test.txt with content 'Hello, World!'\"{Colors.END}")
    print("   You should see an approval request in your configured platform(s)!")

    print("\n" + "─" * 70)
    print(f"{Colors.GREEN}✓ All setup files have been generated!{Colors.END}")
    print(f"{Colors.GREEN}✓ Virtual environment created with all dependencies{Colors.END}")

    enabled_platforms = []
    if slack_config.get("enabled"):
        enabled_platforms.append("Slack")
    if webex_config.get("enabled"):
        enabled_platforms.append("Webex")
    if teams_config.get("enabled"):
        enabled_platforms.append("Teams")

    if enabled_platforms:
        platforms_str = ", ".join(enabled_platforms)
        print(f"{Colors.GREEN}✓ Configured platforms: {platforms_str}{Colors.END}")

    if any_webhook and ngrok_config:
        print(f"{Colors.GREEN}✓ ngrok configuration created for webhook tunneling{Colors.END}")
    print("─" * 70)

    print(f"\n📚 For more information, see:")
    print(f"   {Colors.CYAN}README.md{Colors.END} - General setup")
    if slack_config.get("enabled"):
        print(f"   {Colors.CYAN}docs/SLACK_SETUP.md{Colors.END} - Slack-specific setup")
    if webex_config.get("enabled"):
        print(f"   {Colors.CYAN}docs/WEBEX_SETUP.md{Colors.END} - Webex-specific setup")
    if teams_config.get("enabled"):
        print(f"   {Colors.CYAN}docs/TEAMS_SETUP.md{Colors.END} - Teams-specific setup")
    print()


def check_setup_complete(project_dir: Path) -> bool:
    """Check if setup is already complete."""
    venv_dir = project_dir / ".venv"
    venv_python = venv_dir / "bin" / "python"
    if platform.system() == "Windows":
        venv_python = venv_dir / "Scripts" / "python.exe"
    
    # Check if venv exists and has Python
    if not venv_python.exists():
        return False
    
    # Check if package is installed
    try:
        result = run_command(
            [str(venv_python), "-m", "pip", "show", "cite-before-act-mcp"],
            check=False
        )
        return result.returncode == 0
    except Exception:
        return False


def load_existing_claude_config(project_dir: Path) -> Optional[Dict[str, Any]]:
    """Load existing Claude Desktop configuration if it exists.
    
    Returns:
        Dictionary of existing server configurations (mcpServers content),
        or None if no config exists
    """
    config_path = project_dir / "claude_desktop_config_generated.json"
    if not config_path.exists():
        return None
    
    try:
        with open(config_path, "r") as f:
            data = json.load(f)
            # Handle both formats: {"mcpServers": {...}} or direct mcpServers dict
            if "mcpServers" in data:
                return data["mcpServers"]
            # If it's already the mcpServers content, return as-is
            return data
    except Exception:
        return None


def generate_server_name(upstream_config: Dict[str, Any], existing_config: Optional[Dict[str, Any]]) -> str:
    """Generate a unique server name for the new configuration.
    
    Format: {upstream-server-name}-cite
    Examples: github-cite, filesystem-cite, custom-server-cite
    
    Args:
        upstream_config: Upstream server configuration
        existing_config: Existing Claude Desktop config (for uniqueness check)
    
    Returns:
        Unique server name like 'github-cite' or 'filesystem-cite'
    """
    # Extract upstream server name from command/args
    command = upstream_config.get("command", "").lower()
    args_str = " ".join(upstream_config.get("args", [])).lower()
    combined = f"{command} {args_str}"
    
    # Determine upstream server name
    upstream_name = None
    
    # Check for known servers
    # Check for remote GitHub server first (HTTP transport)
    if upstream_config.get("transport") == "http" and "githubcopilot.com" in upstream_config.get("url", ""):
        upstream_name = "github-remote"
    elif "github" in command or "github-mcp-server" in command:
        upstream_name = "github"
    elif "filesystem" in command or "server-filesystem" in combined:
        upstream_name = "filesystem"
    elif "npx" in command and "@modelcontextprotocol/server-filesystem" in args_str:
        upstream_name = "filesystem"
    else:
        # For custom servers, try to extract a meaningful name
        # Remove common prefixes/suffixes and file extensions
        if command:
            # Use the command name (without path)
            upstream_name = Path(command).stem.lower()
            # Remove common prefixes
            upstream_name = upstream_name.replace("mcp-", "").replace("server-", "").replace("-server", "")
            # If it's still too generic, try to get something from args
            if upstream_name in ("python", "node", "npx", "npm", "go", "rust"):
                # Look for package/server name in args
                for arg in upstream_config.get("args", []):
                    arg_lower = arg.lower()
                    if "server" in arg_lower or "mcp" in arg_lower:
                        # Extract meaningful part
                        parts = arg_lower.replace("@", "").replace("/", "-").split("-")
                        # Find the most meaningful part (usually the last non-generic part)
                        for part in reversed(parts):
                            if part and part not in ("server", "mcp", "protocol", "model", "context"):
                                upstream_name = part
                                break
                        break
        else:
            upstream_name = "custom"
    
    # Sanitize the name (remove invalid characters, ensure it's a valid identifier)
    upstream_name = upstream_name.replace("_", "-").replace(" ", "-")
    # Remove any remaining invalid characters
    upstream_name = "".join(c for c in upstream_name if c.isalnum() or c == "-")
    # Remove leading/trailing dashes and collapse multiple dashes
    upstream_name = "-".join(part for part in upstream_name.split("-") if part)
    
    # If we couldn't determine a name, use a default
    if not upstream_name or upstream_name == "-":
        upstream_name = "mcp"
    
    # Create base name with -cite suffix
    base_name = f"{upstream_name}-cite"
    
    # If no existing config, use base name
    if not existing_config:
        return base_name
    
    # Check if base name is available
    if base_name not in existing_config:
        return base_name
    
    # Find a unique name by appending a number
    counter = 2
    while f"{base_name}-{counter}" in existing_config:
        counter += 1
    
    return f"{base_name}-{counter}"


def merge_claude_config(existing_config: Optional[Dict[str, Any]], new_config: Dict[str, Any], server_name: str) -> Dict[str, Any]:
    """Merge new configuration with existing Claude Desktop configuration."""
    if not existing_config:
        return {server_name: new_config}
    
    merged = existing_config.copy()
    merged[server_name] = new_config
    return merged


def main():
    """Main setup function."""
    print_header("Cite-Before-Act MCP - Interactive Setup")

    # Get project directory
    project_dir = Path(__file__).parent.resolve()
    
    # Check if setup is already complete
    setup_complete = check_setup_complete(project_dir)
    existing_claude_config = load_existing_claude_config(project_dir)
    
    mode = "full"
    if setup_complete:
        print("Detected existing setup. Choose an option:\n")
        print("  1. Full Setup (reconfigure everything)")
        print("  2. Add New MCP Server (add another upstream server configuration)")
        print()
        
        choice = prompt("Choose option (1/2)", "2")
        if choice == "1":
            mode = "full"
            print("\nProceeding with full setup...")
        else:
            mode = "add_server"
            print("\nAdding new MCP server configuration...")
            print("(Will check dependencies, but skipping venv creation and Slack setup)\n")
    
    if mode == "full":
        print("This wizard will guide you through setting up Cite-Before-Act MCP.\n")
        print("We'll configure:")
        print("  • Python virtual environment")
        print("  • Dependencies")
        print("  • Slack integration (optional)")
        print("  • Webhook server with ngrok (optional)")
        print("  • Claude Desktop configuration")
        print()

        if not prompt_yes_no("Ready to begin?", default=True):
            print("Setup cancelled.")
            return 1

    if mode == "full":
        # Step 1: Check prerequisites and select Python
        print_step(1, 7, "Selecting Python Version")

        python_exe = select_python_version()
        if not python_exe:
            return 1

        # Warn if running with a different Python version than selected
        current_python = sys.executable
        if current_python != python_exe:
            current_version = f"{sys.version_info.major}.{sys.version_info.minor}"
            print_warning(f"Script is running with Python {current_version} ({current_python})")
            print_warning(f"But will create venv with: {python_exe}")
            print_warning("This is usually fine, but if you encounter issues, try running the script")
            print_warning(f"with the selected Python: {python_exe} setup_wizard.py")
            print()

        print()
        has_node = check_node_installed()
        if not has_node:
            print_warning("Node.js is recommended for upstream MCP servers")
            if not prompt_yes_no("Continue without Node.js?", default=False):
                print("\nInstall Node.js from: https://nodejs.org/")
                return 1

        # Step 2: Create virtual environment
        print_step(2, 7, "Creating Virtual Environment")
        venv_dir = create_venv(project_dir, python_exe)

        # Step 3: Install dependencies
        print_step(3, 7, "Installing Dependencies")
        install_dependencies(venv_dir, project_dir)

        # Step 4: Configure messaging platforms
        print_step(4, 7, "Configuring Messaging Platforms")
        slack_config = configure_slack()
        webex_config = configure_webex()
        teams_config = configure_teams()

        # Step 5: Configure ngrok (if needed)
        print_step(5, 7, "Configuring ngrok")
        ngrok_config = configure_ngrok(slack_config, webex_config, teams_config)

        # Step 6: Configure upstream server
        print_step(6, 7, "Configuring Upstream MCP Server")
        upstream_config = configure_upstream()

        # Step 7: Generate configuration files
        print_step(7, 7, "Generating Configuration Files")

        # Generate .env
        generate_env_file(project_dir, slack_config, webex_config, teams_config, upstream_config)

        # Generate Claude Desktop config
        server_name = generate_server_name(upstream_config, existing_claude_config)
        claude_config_entry = generate_claude_config(project_dir, venv_dir, slack_config, upstream_config)
        merged_config = merge_claude_config(existing_claude_config, claude_config_entry["cite-before-act"], server_name)

        # Save config (all secrets now in .env, not in Claude Desktop config)
        final_config = {"mcpServers": merged_config}
        save_claude_config(final_config, project_dir)

        # Create ngrok policy if needed
        if ngrok_config and slack_config.get("signing_secret"):
            create_ngrok_policy(project_dir, slack_config["signing_secret"])

        # Create startup scripts
        create_startup_scripts(project_dir, venv_dir, slack_config, webex_config, teams_config, ngrok_config)

        # Print final instructions
        print_final_instructions(project_dir, slack_config, webex_config, teams_config, ngrok_config, {"mcpServers": merged_config})

    else:
        # Add new server mode
        # Use existing venv
        venv_dir = project_dir / ".venv"
        venv_python = venv_dir / "bin" / "python"
        if platform.system() == "Windows":
            venv_python = venv_dir / "Scripts" / "python.exe"
        
        if not venv_python.exists():
            print_error("Virtual environment not found. Please run full setup first.")
            return 1
        
        # Check if dependencies need updating (e.g., after git pull with new requirements)
        print_step(1, 3, "Checking Dependencies")
        missing_deps = []
        required_deps = ["httpx", "fastmcp", "slack-sdk", "pydantic", "python-dotenv"]
        
        for dep in required_deps:
            result = run_command(
                [str(venv_python), "-m", "pip", "show", dep],
                check=False
            )
            if result.returncode != 0:
                missing_deps.append(dep)
        
        if missing_deps:
            print_warning(f"Missing dependencies detected: {', '.join(missing_deps)}")
            print("This can happen after updating the code (e.g., git pull) with new requirements.")
            if prompt_yes_no("\nUpdate dependencies now?", default=True):
                print("Updating dependencies...")
                # Install/upgrade dependencies from requirements.txt
                run_command(
                    [str(venv_python), "-m", "pip", "install", "-r", str(project_dir / "requirements.txt")]
                )
                # Also reinstall the package in editable mode to pick up any code changes
                run_command(
                    [str(venv_python), "-m", "pip", "install", "--use-pep517", "-e", "."],
                    cwd=project_dir
                )
                print_success("Dependencies updated")
            else:
                print_warning("Skipping dependency update. The new server configuration may not work without required packages.")
        else:
            print_success("All dependencies are installed")
        
        # Load existing platform configs from .env if it exists
        slack_config = {"enabled": False}
        webex_config = {"enabled": False}
        teams_config = {"enabled": False}
        env_path = project_dir / ".env"
        if env_path.exists():
            # Try to load platform configs from .env
            with open(env_path, "r") as f:
                for line in f:
                    # Slack
                    if line.startswith("ENABLE_SLACK="):
                        slack_config["enabled"] = line.split("=", 1)[1].strip().lower() == "true"
                    elif line.startswith("SLACK_BOT_TOKEN="):
                        slack_config["bot_token"] = line.split("=", 1)[1].strip()
                    elif line.startswith("SLACK_CHANNEL="):
                        slack_config["channel"] = line.split("=", 1)[1].strip()
                    elif line.startswith("SLACK_USER_ID="):
                        slack_config["user_id"] = line.split("=", 1)[1].strip()
                    # Webex
                    elif line.startswith("ENABLE_WEBEX="):
                        webex_config["enabled"] = line.split("=", 1)[1].strip().lower() == "true"
                    elif line.startswith("WEBEX_BOT_TOKEN="):
                        webex_config["bot_token"] = line.split("=", 1)[1].strip()
                    elif line.startswith("WEBEX_ROOM_ID="):
                        webex_config["room_id"] = line.split("=", 1)[1].strip()
                    elif line.startswith("WEBEX_PERSON_EMAIL="):
                        webex_config["person_email"] = line.split("=", 1)[1].strip()
                    # Teams
                    elif line.startswith("ENABLE_TEAMS="):
                        teams_config["enabled"] = line.split("=", 1)[1].strip().lower() == "true"
                    elif line.startswith("TEAMS_APP_ID="):
                        teams_config["app_id"] = line.split("=", 1)[1].strip()
                    elif line.startswith("TEAMS_APP_PASSWORD="):
                        teams_config["app_password"] = line.split("=", 1)[1].strip()
        
        # Configure upstream server
        print_step(2, 3, "Configuring Upstream MCP Server")
        upstream_config = configure_upstream()
        
        # Generate configuration
        print_step(3, 3, "Generating Configuration")
        
        # Generate Claude Desktop config entry
        server_name = generate_server_name(upstream_config, existing_claude_config)
        claude_config_entry = generate_claude_config(project_dir, venv_dir, slack_config, upstream_config)
        merged_config = merge_claude_config(existing_claude_config, claude_config_entry["cite-before-act"], server_name)

        # Save config (all secrets now in .env, not in Claude Desktop config)
        final_config = {"mcpServers": merged_config}
        save_claude_config(final_config, project_dir)
        
        print_success(f"Added new MCP server configuration: {server_name}")
        print(f"\n{Colors.BOLD}Next Steps:{Colors.END}")
        print(f"1. Review the generated configuration:")
        print(f"   {Colors.CYAN}claude_desktop_config_generated.json{Colors.END}")
        print(f"2. Copy the '{server_name}' entry to your Claude Desktop config file")
        print(f"3. Restart Claude Desktop")
        
        if existing_claude_config:
            print(f"\n{Colors.YELLOW}Note:{Colors.END} Your existing configurations are preserved:")
            for existing_name in existing_claude_config.keys():
                print(f"  • {existing_name}")

    return 0


if __name__ == "__main__":
    # Don't run interactive setup if being called by pip/setuptools
    # (when pip install -e . calls this as a build backend)
    if any(arg in sys.argv for arg in ['egg_info', 'editable_wheel', 'dist_info']):
        # This is being called as a build backend, not as the interactive setup
        # setuptools will handle this automatically
        pass
    else:
        # This is the interactive setup wizard
        try:
            sys.exit(main())
        except KeyboardInterrupt:
            print("\n\nSetup cancelled by user.")
            sys.exit(1)
        except Exception as e:
            print_error(f"\nSetup failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
