#!/usr/bin/env python3
"""Interactive setup script for Cite-Before-Act MCP.

This script guides you through the complete setup process:
1. Creates virtual environment
2. Installs dependencies
3. Configures Slack integration (optional)
4. Sets up ngrok for webhooks (optional)
5. Generates Claude Desktop configuration
6. Creates startup scripts

Run: python3 setup.py
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

    print("Installing project dependencies...")
    run_command([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"])
    run_command([str(python_exe), "-m", "pip", "install", "-e", "."], cwd=project_dir)

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
    print("2. Custom Server (your own MCP server)")

    choice = prompt("Choose option (1/2)", "1")

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
        "# Generated by setup.py",
        "",
        "# Upstream Server Configuration",
        f"UPSTREAM_COMMAND={upstream_config['command']}",
        f"UPSTREAM_ARGS={','.join(upstream_config['args'])}",
        f"UPSTREAM_TRANSPORT={upstream_config['transport']}",
        "",
    ]

    if upstream_config.get("url"):
        lines.append(f"UPSTREAM_URL={upstream_config['url']}")
        lines.append("")

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
            else:
                lines.append("SECURITY_MODE=local")

        lines.append("")

    with open(env_path, "w") as f:
        f.write("\n".join(lines))

    print_success(f"Created .env file: {env_path}")


def generate_claude_config(project_dir: Path, venv_dir: Path, upstream_config: Dict[str, Any]) -> Dict[str, Any]:
    """Generate Claude Desktop MCP configuration."""
    python_exe = get_venv_python(venv_dir)

    config = {
        "cite-before-act": {
            "command": str(python_exe),
            "args": ["-m", "server.main", "--transport", "stdio"],
            "env": {
                "UPSTREAM_COMMAND": upstream_config["command"],
                "UPSTREAM_ARGS": ",".join(upstream_config["args"]),
                "UPSTREAM_TRANSPORT": upstream_config["transport"],
                "USE_LOCAL_APPROVAL": "true",
                "USE_NATIVE_DIALOG": "true",
            }
        }
    }

    if upstream_config.get("url"):
        config["cite-before-act"]["env"]["UPSTREAM_URL"] = upstream_config["url"]

    return config


def save_claude_config(config: Dict[str, Any], project_dir: Path) -> None:
    """Save Claude Desktop configuration to file."""
    config_path = project_dir / "claude_desktop_config_generated.json"

    with open(config_path, "w") as f:
        json.dump({"mcpServers": config}, f, indent=2)

    print_success(f"Saved configuration: {config_path}")


def create_ngrok_policy(project_dir: Path, signing_secret: str) -> Path:
    """Create ngrok traffic policy file."""
    policy_path = project_dir / "ngrok-slack-policy.yml"

    content = f"""# ngrok Traffic Policy for Slack Webhook Verification
# Generated by setup.py
#
# This policy validates Slack request signatures at the tunnel level
# before forwarding requests to your application.
#
# Learn more: https://ngrok.com/docs/integrations/webhooks/slack-webhooks

on_http_request:
  - actions:
      - type: "webhook-verification"
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
        content = f"""@echo off
REM Start Slack Webhook Server
REM Generated by setup.py

echo Starting Slack Webhook Server...
"{python_exe}" examples\\slack_webhook_server.py
"""
        if ngrok_config:
            ngrok_script = project_dir / "start_ngrok.bat"
            port = ngrok_config.get("port", "3000")
            ngrok_content = f"""@echo off
REM Start ngrok tunnel with Slack verification
REM Generated by setup.py

echo Starting ngrok tunnel on port {port}...
ngrok http {port} --traffic-policy-file ngrok-slack-policy.yml
"""
            with open(ngrok_script, "w") as f:
                f.write(ngrok_content)
            print_success(f"Created: {ngrok_script}")
    else:
        # Unix shell script
        script_path = project_dir / "start_webhook.sh"
        content = f"""#!/bin/bash
# Start Slack Webhook Server
# Generated by setup.py

echo "Starting Slack Webhook Server..."
"{python_exe}" examples/slack_webhook_server.py
"""
        with open(script_path, "w") as f:
            f.write(content)
        script_path.chmod(0o755)  # Make executable

        if ngrok_config:
            ngrok_script = project_dir / "start_ngrok.sh"
            port = ngrok_config.get("port", "3000")
            ngrok_content = f"""#!/bin/bash
# Start ngrok tunnel with Slack verification
# Generated by setup.py

echo "Starting ngrok tunnel on port {port}..."
ngrok http {port} --traffic-policy-file ngrok-slack-policy.yml
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


def main():
    """Main setup function."""
    print_header("Cite-Before-Act MCP - Interactive Setup")

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

    # Get project directory
    project_dir = Path(__file__).parent.resolve()

    # Step 1: Check prerequisites and select Python
    print_step(1, 7, "Selecting Python Version")

    python_exe = select_python_version()
    if not python_exe:
        return 1

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
    claude_config = generate_claude_config(project_dir, venv_dir, upstream_config)
    save_claude_config(claude_config, project_dir)

    # Create ngrok policy if needed
    if ngrok_config and slack_config.get("signing_secret"):
        create_ngrok_policy(project_dir, slack_config["signing_secret"])

    # Create startup scripts
    create_startup_scripts(project_dir, venv_dir, slack_config, ngrok_config)

    # Print final instructions
    print_final_instructions(project_dir, slack_config, ngrok_config, claude_config)

    return 0


if __name__ == "__main__":
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
