"""Local approval mechanism using CLI prompts."""

import asyncio
import json
import os
import sys
import time
import uuid
from typing import Optional


class LocalApproval:
    """Local approval handler using CLI prompts."""

    def __init__(self, use_gui: bool = True):
        """Initialize local approval handler.

        Args:
            use_gui: If True, try to use GUI dialogs (requires tkinter). Default True for stdio MCP.
        """
        self.use_gui = use_gui

    async def request_approval(
        self,
        tool_name: str,
        description: str,
        arguments: dict,
    ) -> bool:
        """Request approval via local prompt.

        Args:
            tool_name: Name of the tool
            description: Description of the action
            arguments: Arguments that would be passed

        Returns:
            True if approved, False if rejected
        """
        if self.use_gui:
            return await self._gui_approval(tool_name, description, arguments)
        else:
            return await self._cli_approval(tool_name, description, arguments)

    async def _cli_approval(
        self,
        tool_name: str,
        description: str,
        arguments: dict,
    ) -> bool:
        """Request approval via CLI prompt.

        Note: For stdio MCP servers, stdin is used for protocol, so we use GUI instead.

        Args:
            tool_name: Name of the tool
            description: Description of the action
            arguments: Arguments that would be passed

        Returns:
            True if approved, False if rejected
        """
        # For stdio MCP, we can't read from stdin, so try GUI first
        # If GUI fails, fall back to a blocking approach that writes to stderr
        try:
            return await self._gui_approval(tool_name, description, arguments)
        except Exception:
            # GUI failed, use a file-based or blocking approach
            import json
            import time
            import uuid

            approval_id = str(uuid.uuid4())
            approval_file = f"/tmp/cite-before-act-approval-{approval_id}.json"

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
            print("\n" + "=" * 70, file=sys.stderr)
            print("🔒 APPROVAL REQUIRED", file=sys.stderr)
            print("=" * 70, file=sys.stderr)
            print(f"Tool: {tool_name}", file=sys.stderr)
            print(f"\nDescription:", file=sys.stderr)
            print(f"  {description}", file=sys.stderr)
            print(f"\nArguments:", file=sys.stderr)
            print(json.dumps(arguments, indent=2), file=sys.stderr)
            print("=" * 70, file=sys.stderr)
            print(f"\n📝 Approval file: {approval_file}", file=sys.stderr)
            print(f"To approve, run:", file=sys.stderr)
            print(f'  echo "approved" > {approval_file}', file=sys.stderr)
            print(f"To reject, run:", file=sys.stderr)
            print(f'  echo "rejected" > {approval_file}', file=sys.stderr)
            print(f"\n⏳ Waiting for approval...", file=sys.stderr)
            sys.stderr.flush()

            # Poll the file for response (with timeout)
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
                                print("✅ Approved", file=sys.stderr)
                                return True
                            elif response == "rejected":
                                os.remove(approval_file)
                                try:
                                    os.remove(info_file)
                                except Exception:
                                    pass
                                print("❌ Rejected", file=sys.stderr)
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
            print("⏱️  Approval timeout - rejected", file=sys.stderr)
            return False

    async def _gui_approval(
        self,
        tool_name: str,
        description: str,
        arguments: dict,
    ) -> bool:
        """Request approval via GUI dialog.

        Args:
            tool_name: Name of the tool
            description: Description of the action
            arguments: Arguments that would be passed

        Returns:
            True if approved, False if rejected
        """
        try:
            import tkinter as tk
            from tkinter import messagebox, scrolledtext
        except ImportError:
            # Fall back to file-based if tkinter not available
            return await self._cli_approval(tool_name, description, arguments)

        import json

        # Create a dialog with more details
        result = [None]  # Use list to modify from nested function

        def show_dialog():
            root = tk.Tk()
            root.title("🔒 Approval Required")
            root.geometry("600x500")
            
            # Create main frame
            frame = tk.Frame(root, padx=20, pady=20)
            frame.pack(fill=tk.BOTH, expand=True)
            
            # Tool name
            tool_label = tk.Label(
                frame,
                text=f"Tool: {tool_name}",
                font=("Arial", 14, "bold"),
            )
            tool_label.pack(anchor=tk.W, pady=(0, 10))
            
            # Description
            desc_label = tk.Label(
                frame,
                text="Description:",
                font=("Arial", 10, "bold"),
            )
            desc_label.pack(anchor=tk.W, pady=(10, 5))
            
            desc_text = tk.Text(
                frame,
                height=3,
                wrap=tk.WORD,
                font=("Arial", 10),
            )
            desc_text.insert("1.0", description)
            desc_text.config(state=tk.DISABLED)
            desc_text.pack(fill=tk.X, pady=(0, 10))
            
            # Arguments
            args_label = tk.Label(
                frame,
                text="Arguments:",
                font=("Arial", 10, "bold"),
            )
            args_label.pack(anchor=tk.W, pady=(10, 5))
            
            args_text = scrolledtext.ScrolledText(
                frame,
                height=8,
                wrap=tk.WORD,
                font=("Courier", 9),
            )
            args_text.insert("1.0", json.dumps(arguments, indent=2))
            args_text.config(state=tk.DISABLED)
            args_text.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
            
            # Buttons
            button_frame = tk.Frame(frame)
            button_frame.pack(fill=tk.X)
            
            def approve():
                result[0] = True
                root.destroy()
            
            def reject():
                result[0] = False
                root.destroy()
            
            approve_btn = tk.Button(
                button_frame,
                text="✅ Approve",
                command=approve,
                bg="#4CAF50",
                fg="white",
                font=("Arial", 12, "bold"),
                padx=20,
                pady=10,
            )
            approve_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 10))
            
            reject_btn = tk.Button(
                button_frame,
                text="❌ Reject",
                command=reject,
                bg="#f44336",
                fg="white",
                font=("Arial", 12, "bold"),
                padx=20,
                pady=10,
            )
            reject_btn.pack(side=tk.LEFT, expand=True, fill=tk.X)
            
            # Make window appear on top
            root.lift()
            root.attributes("-topmost", True)
            root.focus_force()
            
            # Center window
            root.update_idletasks()
            width = root.winfo_width()
            height = root.winfo_height()
            x = (root.winfo_screenwidth() // 2) - (width // 2)
            y = (root.winfo_screenheight() // 2) - (height // 2)
            root.geometry(f"{width}x{height}+{x}+{y}")
            
            root.mainloop()

        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, show_dialog)

        return result[0] if result[0] is not None else False

