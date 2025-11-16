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


def configure_ngrok(slack_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Configure ngrok for webhooks."""
    if not slack_config.get("webhook_enabled") or slack_config.get("webhook_hosting") != "ngrok":
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
        # GitHub MCP server
        print("\n" + "─" * 70)
        print("GitHub MCP Server Setup")
        print("─" * 70)
        print("\nChoose how to connect to GitHub MCP Server:")
        print("  1. Remote Server (HTTP) - Recommended")
        print("     • Uses GitHub's hosted MCP server at api.githubcopilot.com")
        print("     • No local installation required")
        print("     • Requires GitHub Personal Access Token")
        print("  2. Local Server (stdio)")
        print("     • Run github-mcp-server binary locally")
        print("     • Requires downloading and installing the binary")
        print("     • Requires GitHub Personal Access Token")
        
        github_choice = prompt("\nChoose option (1/2)", "1")
        
        if github_choice == "1":
            # Remote GitHub MCP server (HTTP)
            print("\n" + "─" * 70)
            print("Remote GitHub MCP Server Configuration")
            print("─" * 70)
            print("\nThis will connect to GitHub's hosted MCP server.")
            print("URL: https://api.githubcopilot.com/mcp/")
            
            # Get GitHub token
            print("\n📝 GitHub Personal Access Token:")
            print("1. Go to: https://github.com/settings/tokens")
            print("2. Generate a new token (classic)")
            print("3. Required scopes: repo, workflow, write:packages, delete:packages, admin:org, etc.")
            print("   (Or use minimal scopes needed for your use case)")
            
            token = prompt("\nGitHub Personal Access Token", "")

            if not token:
                print_warning("No token provided. You'll need to set GITHUB_PERSONAL_ACCESS_TOKEN in your .env file")

            config = {
                "url": "https://api.githubcopilot.com/mcp/",
                "transport": "http",
                "github_token": token  # This will be saved to .env only
            }
            
            return config
        else:
            # Local GitHub MCP server (stdio)
            print("\n" + "─" * 70)
            print("Local GitHub MCP Server Configuration")
            print("─" * 70)
            print("\nThis will use a local github-mcp-server binary.")
            print("\nYou'll need:")
            print("1. GitHub MCP Server binary (download from https://github.com/github/github-mcp-server/releases)")
            print("2. GitHub Personal Access Token (create at https://github.com/settings/tokens)")

            # Check if github-mcp-server is in PATH
            import shutil
            github_mcp_path = shutil.which("github-mcp-server")
            if github_mcp_path:
                print_success(f"Found github-mcp-server at: {github_mcp_path}")
                command = "github-mcp-server"
            else:
                print_warning("github-mcp-server not found in PATH")
                custom_path = prompt("Enter full path to github-mcp-server binary (or press Enter to use 'github-mcp-server')", "")
                if custom_path:
                    command = custom_path
                else:
                    command = "github-mcp-server"
                    print_warning("Using 'github-mcp-server' - ensure it's in PATH or configuration will fail")

            # Get GitHub token
            print("\n📝 GitHub Personal Access Token:")
            print("Required scopes: repo, workflow, write:packages, delete:packages, admin:org, etc.")
            print("Or use minimal scopes needed for your use case")
            token = prompt("GitHub Personal Access Token", "")
            
            if not token:
                print_warning("No token provided. You'll need to set GITHUB_PERSONAL_ACCESS_TOKEN in your .env file")

            # GitHub MCP server requires 'stdio' subcommand
            args = ["stdio"]
            
            # Optional: additional flags
            print("\nOptional GitHub MCP Server flags:")
            print("Common options: --read-only, --lockdown-mode, --dynamic-toolsets")
            additional_args_str = prompt("Additional arguments (comma-separated, or press Enter for none)", "")
            if additional_args_str:
                args.extend([arg.strip() for arg in additional_args_str.split(",")])

            config = {
                "command": command,
                "args": args,
                "transport": "stdio",
                "github_token": token
            }

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


def generate_env_file(project_dir: Path, slack_config: Dict[str, Any], upstream_config: Dict[str, Any]) -> None:
    """Generate .env file."""
    env_path = project_dir / ".env"

    if env_path.exists():
        if not prompt_yes_no(f"\n.env file already exists. Overwrite?", default=False):
            print_warning("Skipping .env generation")
            return

    print("\nGenerating .env file...")

    lines = [
        "# Cite-Before-Act MCP Configuration",
        "# Generated by setup_wizard.py",
        "",
        "# Detection Settings",
        "# Allowlist: Explicitly mark these tools as mutating (additive, not exclusive)",
        "# Convention and metadata detection will still work for other tools",
    ]
    
    # Set defaults based on upstream server type
    is_github = (
        upstream_config.get("command") == "github-mcp-server" 
        or "github" in upstream_config.get("command", "").lower()
        or upstream_config.get("transport") == "http" and "githubcopilot.com" in upstream_config.get("url", "")
    )
    
    if is_github:
        # GitHub MCP server defaults
        lines.extend([
            "DETECTION_ALLOWLIST=",
            "# Blocklist: Explicitly mark these tools as non-mutating (override convention/metadata)",
            "DETECTION_BLOCKLIST=read_file,get_file,list_files,search_code,get_issue,list_issues,get_pull_request,list_pull_requests",
        ])
    else:
        # Filesystem server defaults
        lines.extend([
            "DETECTION_ALLOWLIST=write_file,edit_file,create_directory,move_file",
            "# Blocklist: Explicitly mark these tools as non-mutating (override convention/metadata)",
            "DETECTION_BLOCKLIST=read_text_file,read_media_file,list_directory,get_file_info",
        ])
    
    lines.extend([
        "DETECTION_ENABLE_CONVENTION=true",
        "DETECTION_ENABLE_METADATA=true",
        "",
        "# Approval Settings",
        "APPROVAL_TIMEOUT_SECONDS=300",
        "USE_LOCAL_APPROVAL=true",
        "",
        "# Upstream Server Configuration",
    ])
    
    # Handle different transport types
    if upstream_config.get("transport") == "http":
        # HTTP transport (remote server)
        lines.append(f"UPSTREAM_URL={upstream_config['url']}")
        lines.append(f"UPSTREAM_TRANSPORT=http")
        lines.append("")

        # Add GitHub token if provided
        if upstream_config.get("github_token"):
            lines.extend([
                "# GitHub Personal Access Token (automatically used by server)",
                "# The server reads this and adds 'Authorization: Bearer <token>' header",
                f"GITHUB_PERSONAL_ACCESS_TOKEN={upstream_config['github_token']}",
                "",
            ])
    else:
        # stdio transport (local server)
        lines.append(f"UPSTREAM_COMMAND={upstream_config['command']}")
        lines.append(f"UPSTREAM_ARGS={','.join(upstream_config['args'])}")
        lines.append(f"UPSTREAM_TRANSPORT={upstream_config['transport']}")
        lines.append("")

        # Add GitHub token if provided
        if upstream_config.get("github_token"):
            lines.extend([
                "# GitHub Personal Access Token (passed to upstream server via env)",
                f"GITHUB_PERSONAL_ACCESS_TOKEN={upstream_config['github_token']}",
                "",
            ])

    if slack_config["enabled"]:
        lines.extend([
            "# Slack Configuration",
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
                "# Webhook Configuration",
                f"SLACK_SIGNING_SECRET={slack_config['signing_secret']}",
            ])

            if slack_config.get("webhook_hosting") == "self-hosted":
                lines.append("SECURITY_MODE=production")
                lines.append("HOST=0.0.0.0  # Listen on all interfaces for production")
            else:
                lines.append("SECURITY_MODE=local")
                lines.append("HOST=127.0.0.1  # Only localhost when using ngrok")
        
        # Set USE_NATIVE_DIALOG based on Slack being enabled
        # When Slack is enabled, disable native dialog to avoid duplicates
        lines.append("USE_NATIVE_DIALOG=false" if slack_config["enabled"] else "USE_NATIVE_DIALOG=true")

        lines.append("")
    else:
        # Slack not enabled - enable native dialog
        lines.append("USE_NATIVE_DIALOG=true")
        lines.append("")

    with open(env_path, "w") as f:
        f.write("\n".join(lines))

    print_success(f"Created .env file: {env_path}")


def generate_claude_config(project_dir: Path, venv_dir: Path, slack_config: Dict[str, Any], upstream_config: Dict[str, Any]) -> Dict[str, Any]:
    """Generate Claude Desktop MCP configuration."""
    python_exe = get_venv_python(venv_dir)

    # Set defaults based on upstream server type
    is_github = (
        upstream_config.get("command") == "github-mcp-server" 
        or "github" in upstream_config.get("command", "").lower()
        or upstream_config.get("transport") == "http" and "githubcopilot.com" in upstream_config.get("url", "")
    )
    
    env = {
        # Detection settings
        # Allowlist is additive - convention/metadata detection still works for other tools
        "DETECTION_ALLOWLIST": "" if is_github else "write_file,edit_file,create_directory,move_file",
        "DETECTION_BLOCKLIST": "read_file,get_file,list_files,search_code,get_issue,list_issues,get_pull_request,list_pull_requests,search_repositories,get_repository,list_repositories,get_user,list_users,search_users" if is_github else "read_text_file,read_media_file,list_directory,get_file_info",
        "DETECTION_ENABLE_CONVENTION": "true",
        "DETECTION_ENABLE_METADATA": "true",
        
        # Approval settings
        "APPROVAL_TIMEOUT_SECONDS": "300",
        "USE_LOCAL_APPROVAL": "true",
    }
    
    # Handle different transport types
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
    
    # Slack configuration
    if slack_config.get("enabled"):
        env["ENABLE_SLACK"] = "true"
        env["SLACK_BOT_TOKEN"] = slack_config.get("bot_token", "")
        
        if slack_config.get("channel"):
            env["SLACK_CHANNEL"] = slack_config["channel"]
        elif slack_config.get("user_id"):
            env["SLACK_USER_ID"] = slack_config["user_id"]
        
        # When Slack is enabled, disable native dialog to avoid duplicates
        env["USE_NATIVE_DIALOG"] = "false"
    else:
        # When Slack is not enabled, enable native dialog
        env["USE_NATIVE_DIALOG"] = "true"
        env["ENABLE_SLACK"] = "false"

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


def create_startup_scripts(project_dir: Path, venv_dir: Path, slack_config: Dict[str, Any], ngrok_config: Optional[Dict[str, Any]]) -> None:
    """Create convenience startup scripts."""
    if not slack_config.get("webhook_enabled"):
        return

    print("\nCreating startup scripts...")

    python_exe = get_venv_python(venv_dir)

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

echo Starting Slack Webhook Server...
"{python_exe}" examples\\slack_webhook_server.py
"""
        if ngrok_config:
            ngrok_script = project_dir / "start_ngrok.bat"
            port = ngrok_config.get("port", "3000")
            policy_file = project_dir / "ngrok-slack-policy.yml"
            ngrok_content = f"""@echo off
REM Start ngrok tunnel
REM Generated by setup_wizard.py
REM
REM NOTE: ngrok webhook-verification requires Pro/Enterprise plan.
REM If you get ERR_NGROK_2201, use application-level verification instead:
REM   1. Edit .env and set: SECURITY_MODE=production
REM   2. Run ngrok without policy: ngrok http {port}
REM   3. The webhook server will handle verification in application code

echo Starting ngrok tunnel on port {port}...

REM Check if policy file exists
if exist "{policy_file}" (
    echo Using ngrok traffic policy (requires Pro/Enterprise plan)...
    echo If you get ERR_NGROK_2201, see instructions in this script's comments
    ngrok http {port} --traffic-policy-file {policy_file}
) else (
    echo Policy file not found. Starting ngrok without verification...
    echo ⚠️  Note: Set SECURITY_MODE=production in .env for application-level verification
    ngrok http {port}
)
"""
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

echo "Starting Slack Webhook Server..."
"{python_exe}" examples/slack_webhook_server.py
"""
        with open(script_path, "w") as f:
            f.write(content)
        script_path.chmod(0o755)  # Make executable

        if ngrok_config:
            ngrok_script = project_dir / "start_ngrok.sh"
            port = ngrok_config.get("port", "3000")
            policy_file = project_dir / "ngrok-slack-policy.yml"
            ngrok_content = f"""#!/bin/bash
# Start ngrok tunnel
# Generated by setup_wizard.py
#
# NOTE: If you get ERR_NGROK_2201, check that your ngrok version supports verify-webhook.
# Fallback: Use application-level verification instead:
#   1. Edit .env and set: SECURITY_MODE=production
#   2. Run ngrok without policy: ngrok http {port}
#   3. The webhook server will handle verification in application code

echo "Starting ngrok tunnel on port {port}..."

# Check if policy file exists
if [ -f "{policy_file}" ]; then
    echo "Using ngrok traffic policy (requires Pro/Enterprise plan)..."
    echo "If you get ERR_NGROK_2201, see instructions in this script's comments"
    ngrok http {port} --traffic-policy-file {policy_file}
else
    echo "Policy file not found. Starting ngrok without verification..."
    echo "⚠️  Note: Set SECURITY_MODE=production in .env for application-level verification"
    ngrok http {port}
fi
"""
            with open(ngrok_script, "w") as f:
                f.write(ngrok_content)
            ngrok_script.chmod(0o755)  # Make executable
            print_success(f"Created: {ngrok_script}")

    with open(script_path, "w") as f:
        f.write(content)

    print_success(f"Created: {script_path}")


def print_final_instructions(project_dir: Path, slack_config: Dict[str, Any], ngrok_config: Optional[Dict[str, Any]], claude_config: Dict[str, Any]) -> None:
    """Print final setup instructions."""
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

    # Slack webhook setup
    if slack_config.get("webhook_enabled"):
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

            print(f"\n{Colors.BOLD}4. Configure Slack Interactive Components:{Colors.END}")
            print("   a. Copy the ngrok URL from the terminal")
            print("   b. Go to: https://api.slack.com/apps → Your App")
            print("   c. Go to: Interactivity & Shortcuts")
            print("   d. Set Request URL to: https://YOUR-NGROK-URL.ngrok.io/slack/interactive")
            print("   e. Save changes")
        else:
            print(f"\n{Colors.BOLD}3. Deploy webhook server to your cloud/VPS{Colors.END}")
            print("   Ensure HTTPS is enabled (required by Slack)")

    print(f"\n{Colors.BOLD}5. Restart Claude Desktop{Colors.END}")
    print("   Completely quit and reopen Claude Desktop")

    print(f"\n{Colors.BOLD}6. Test the Setup:{Colors.END}")
    print("   In Claude Desktop, try:")
    print(f"   {Colors.CYAN}\"Create a file called test.txt with content 'Hello, World!'\"{Colors.END}")
    print("   You should see an approval request!")

    print("\n" + "─" * 70)
    print(f"{Colors.GREEN}✓ All setup files have been generated!{Colors.END}")
    print(f"{Colors.GREEN}✓ Virtual environment created with all dependencies{Colors.END}")
    if slack_config.get("webhook_enabled") and ngrok_config:
        print(f"{Colors.GREEN}✓ ngrok traffic policy created for secure webhooks{Colors.END}")
    print("─" * 70)

    print(f"\n📚 For more information, see: {Colors.CYAN}README.md{Colors.END}\n")


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

        # Step 4: Configure Slack
        print_step(4, 7, "Configuring Slack Integration")
        slack_config = configure_slack()

        # Step 5: Configure ngrok (if needed)
        print_step(5, 7, "Configuring ngrok")
        ngrok_config = configure_ngrok(slack_config)

        # Step 6: Configure upstream server
        print_step(6, 7, "Configuring Upstream MCP Server")
        upstream_config = configure_upstream()

        # Step 7: Generate configuration files
        print_step(7, 7, "Generating Configuration Files")

        # Generate .env
        generate_env_file(project_dir, slack_config, upstream_config)

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
        create_startup_scripts(project_dir, venv_dir, slack_config, ngrok_config)

        # Print final instructions
        print_final_instructions(project_dir, slack_config, ngrok_config, {"mcpServers": merged_config})

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
        
        # Load existing Slack config from .env if it exists
        slack_config = {"enabled": False}
        env_path = project_dir / ".env"
        if env_path.exists():
            # Try to load Slack config from .env
            with open(env_path, "r") as f:
                for line in f:
                    if line.startswith("ENABLE_SLACK="):
                        slack_config["enabled"] = line.split("=", 1)[1].strip().lower() == "true"
                    elif line.startswith("SLACK_BOT_TOKEN="):
                        slack_config["bot_token"] = line.split("=", 1)[1].strip()
                    elif line.startswith("SLACK_CHANNEL="):
                        slack_config["channel"] = line.split("=", 1)[1].strip()
                    elif line.startswith("SLACK_USER_ID="):
                        slack_config["user_id"] = line.split("=", 1)[1].strip()
        
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
