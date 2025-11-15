"""Local approval mechanism using native OS dialogs and file-based approval."""

import asyncio
import json
import os
import platform
import subprocess
import sys
import time
import uuid
from typing import Optional


class LocalApproval:
    """Local approval handler using native OS dialogs and file-based approval."""

    def __init__(self, use_native_dialog: bool = True, use_file_based: bool = True):
        """Initialize local approval handler.

        Args:
            use_native_dialog: If True, try to use native OS dialogs (macOS/Windows)
            use_file_based: If True, always show file-based approval instructions (works on all platforms)
        """
        self.use_native_dialog = use_native_dialog
        self.use_file_based = use_file_based
        self.platform = platform.system()

    async def request_approval(
        self,
        tool_name: str,
        description: str,
        arguments: dict,
    ) -> bool:
        """Request approval via multiple methods simultaneously.

        This method triggers:
        - Native OS dialog (macOS/Windows) if enabled
        - File-based approval (always enabled, works on all platforms)
        - All methods write to the same approval file, so any one can approve

        Args:
            tool_name: Name of the tool
            description: Description of the action
            arguments: Arguments that would be passed

        Returns:
            True if approved, False if rejected
        """
        approval_id = str(uuid.uuid4())
        approval_file = f"/tmp/cite-before-act-approval-{approval_id}.json"
        
        # Always set up file-based approval (works on all platforms)
        # This also serves as the shared state for all approval methods
        asyncio.create_task(self._setup_file_based_approval(
            approval_id, approval_file, tool_name, description, arguments
        ))
        
        # Try native dialog in parallel (macOS/Windows)
        if self.use_native_dialog:
            asyncio.create_task(self._try_native_dialog(
                approval_file, tool_name, description, arguments
            ))
        
        # Poll for approval response (from any method)
        return await self._wait_for_approval_response(approval_file, approval_id)

    async def _setup_file_based_approval(
        self,
        approval_id: str,
        approval_file: str,
        tool_name: str,
        description: str,
        arguments: dict,
    ) -> None:
        """Set up file-based approval and print instructions to logs.
        
        Args:
            approval_id: Unique approval ID
            approval_file: Path to approval file
            tool_name: Name of the tool
            description: Description of the action
            arguments: Arguments that would be passed
        """
        # Write approval request info to file (for user reference)
        request_data = {
            "approval_id": approval_id,
            "tool_name": tool_name,
            "description": description,
            "arguments": arguments,
        }
        info_file = f"{approval_file}.info"
        with open(info_file, "w") as f:
            json.dump(request_data, f, indent=2)

        # Print to stderr (visible in Claude Desktop logs)
        print("\n" + "=" * 70, file=sys.stderr, flush=True)
        print("🔒 APPROVAL REQUIRED", file=sys.stderr, flush=True)
        print("=" * 70, file=sys.stderr, flush=True)
        print(f"Tool: {tool_name}", file=sys.stderr, flush=True)
        print(f"\nDescription:", file=sys.stderr, flush=True)
        print(f"  {description}", file=sys.stderr, flush=True)
        print(f"\nArguments:", file=sys.stderr, flush=True)
        print(json.dumps(arguments, indent=2), file=sys.stderr, flush=True)
        print("=" * 70, file=sys.stderr, flush=True)
        print(f"\n📝 To approve via file (works on all platforms):", file=sys.stderr, flush=True)
        print(f'  echo "approved" > {approval_file}', file=sys.stderr, flush=True)
        print(f"📝 To reject via file:", file=sys.stderr, flush=True)
        print(f'  echo "rejected" > {approval_file}', file=sys.stderr, flush=True)
        print(f"\n⏳ Waiting for approval...", file=sys.stderr, flush=True)
    
    async def _try_native_dialog(
        self,
        approval_file: str,
        tool_name: str,
        description: str,
        arguments: dict,
    ) -> None:
        """Try to show native OS dialog (macOS/Windows).
        
        This runs in the background and writes to the approval file when user responds.
        
        Args:
            approval_file: Path to approval file
            tool_name: Name of the tool
            description: Description of the action
            arguments: Arguments that would be passed
        """
        if self.platform == "Darwin":  # macOS
            await self._macos_dialog(approval_file, tool_name, description, arguments)
        elif self.platform == "Windows":
            await self._windows_dialog(approval_file, tool_name, description, arguments)
        # Linux: no native dialog, use file-based only
    
    async def _macos_dialog(
        self,
        approval_file: str,
        tool_name: str,
        description: str,
        arguments: dict,
    ) -> None:
        """Show native macOS dialog using osascript.
        
        Uses a simple display dialog that doesn't require System Events permissions.
        
        Args:
            approval_file: Path to approval file
            tool_name: Name of the tool
            description: Description of the action
            arguments: Arguments that would be passed
        """
        try:
            # Format a concise message for dialog (macOS dialogs have limited space)
            # Show key info: tool name, description, and key arguments
            args_summary = []
            for key, value in arguments.items():
                if isinstance(value, str):
                    # Truncate long strings
                    display_value = value[:60] + "..." if len(value) > 60 else value
                    args_summary.append(f"{key}: {display_value}")
                elif isinstance(value, (int, float, bool)):
                    args_summary.append(f"{key}: {value}")
                else:
                    args_summary.append(f"{key}: {type(value).__name__}")
            
            args_text = "\n".join(args_summary) if args_summary else "No arguments"
            
            # Create a concise message (macOS dialogs work better with shorter text)
            message = f"Tool: {tool_name}\n\n{description}\n\nParameters:\n{args_text}"
            
            # Use a more robust approach: write message to temp file and read it
            # This avoids escaping issues with complex messages
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                f.write(message)
                temp_msg_file = f.name
            
            # Create AppleScript WITHOUT System Events (no permissions needed!)
            # Just use display dialog directly - it doesn't require any special permissions
            script = f'''
            set msgFile to open for access file POSIX file "{temp_msg_file}"
            set msgContent to read msgFile
            close access msgFile
            
            -- Simple display dialog (no System Events needed, no permissions required)
            set response to display dialog msgContent buttons {{"Reject", "Approve"}} default button "Approve" with title "🔒 Approval Required" with icon caution
            set buttonPressed to button returned of response
            if buttonPressed is "Approve" then
                do shell script "echo approved > {approval_file}"
            else
                do shell script "echo rejected > {approval_file}"
            end if
            
            do shell script "rm {temp_msg_file}"
            '''
            
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    timeout=300,  # 5 minute timeout
                )
            )
        except subprocess.TimeoutExpired:
            # Dialog timed out - user didn't respond
            pass
        except Exception as e:
            # Dialog failed - file-based approval will still work
            print(f"Native macOS dialog failed: {e}", file=sys.stderr, flush=True)
    
    async def _windows_dialog(
        self,
        approval_file: str,
        tool_name: str,
        description: str,
        arguments: dict,
    ) -> None:
        """Show native Windows dialog using PowerShell.
        
        Args:
            approval_file: Path to approval file
            tool_name: Name of the tool
            description: Description of the action
            arguments: Arguments that would be passed
        """
        try:
            # Format message for dialog
            args_text = json.dumps(arguments, indent=2)
            message = f"Tool: {tool_name}\n\nDescription:\n{description}\n\nArguments:\n{args_text}"
            
            # Use a more robust approach: write message to temp file and read it
            # This avoids escaping issues with complex messages
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                f.write(message)
                temp_msg_file = f.name
            
            # Note: Windows uses different path format
            win_approval_file = approval_file.replace('/', '\\')
            win_temp_file = temp_msg_file.replace('/', '\\')
            
            # Create PowerShell script to show dialog
            script = f'''
            $message = Get-Content -Path "{win_temp_file}" -Raw
            Add-Type -AssemblyName System.Windows.Forms
            $result = [System.Windows.Forms.MessageBox]::Show(
                $message,
                "🔒 Approval Required",
                [System.Windows.Forms.MessageBoxButtons]::YesNo,
                [System.Windows.Forms.MessageBoxIcon]::Warning
            )
            if ($result -eq "Yes") {{
                "approved" | Out-File -FilePath "{win_approval_file}" -Encoding utf8
            }} else {{
                "rejected" | Out-File -FilePath "{win_approval_file}" -Encoding utf8
            }}
            Remove-Item -Path "{win_temp_file}" -Force
            '''
            
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    ["powershell", "-Command", script],
                    capture_output=True,
                    timeout=300,  # 5 minute timeout
                )
            )
        except subprocess.TimeoutExpired:
            # Dialog timed out - user didn't respond
            pass
        except Exception as e:
            # Dialog failed - file-based approval will still work
            print(f"Native Windows dialog failed: {e}", file=sys.stderr, flush=True)
    
    async def _wait_for_approval_response(
        self,
        approval_file: str,
        approval_id: str,
    ) -> bool:
        """Wait for approval response from any method (native dialog or file).
        
        Args:
            approval_file: Path to approval file
            approval_id: Unique approval ID
            
        Returns:
            True if approved, False if rejected or timed out
        """
        info_file = f"{approval_file}.info"
        timeout = 300  # 5 minutes
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                if os.path.exists(approval_file):
                    with open(approval_file, "r") as f:
                        response = f.read().strip().lower()
                        if response == "approved":
                            os.remove(approval_file)
                            try:
                                os.remove(info_file)
                            except Exception:
                                pass
                            print("✅ Approved", file=sys.stderr, flush=True)
                            return True
                        elif response == "rejected":
                            os.remove(approval_file)
                            try:
                                os.remove(info_file)
                            except Exception:
                                pass
                            print("❌ Rejected", file=sys.stderr, flush=True)
                            return False
            except Exception:
                pass
            await asyncio.sleep(0.5)  # Check every 500ms

        # Timeout
        try:
            if os.path.exists(approval_file):
                os.remove(approval_file)
            if os.path.exists(info_file):
                os.remove(info_file)
        except Exception:
            pass
        print("⏱️  Approval timeout - rejected", file=sys.stderr, flush=True)
        return False

