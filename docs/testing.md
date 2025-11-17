# Testing the Setup

Once you've configured Claude Desktop, use these tests to verify everything works correctly.

## End-to-End Test Workflow

### 1. Test Non-Mutating Operation (Immediate)

In Claude Desktop, type:
```
List the contents of ~/mcp-test-workspace
```

**Expected:** Returns directory listing immediately without approval.

### 2. Test File Creation (Requires Approval)

In Claude Desktop, type:
```
Create a file called test.txt in ~/mcp-test-workspace with the content 'Hello, World!'
```

**Expected:**
- **If Slack NOT configured**: Native dialog appears (macOS/Windows) + file-based instructions in logs
- **If Slack configured**: Approval request sent to Slack channel + file-based instructions in logs (no popup)

Click **Approve** in the dialog or Slack, or approve via file:
```bash
echo "approved" > /tmp/cite-before-act-approval-{id}.json
```

### 3. Test File Reading (Immediate)

In Claude Desktop, type:
```
Read the file ~/mcp-test-workspace/test.txt
```

**Expected:** Returns file contents immediately without approval.

### 4. Test File Deletion (Requires Approval)

In Claude Desktop, type:
```
Delete the file ~/mcp-test-workspace/test.txt
```

**Expected:** Approval request appears (native dialog, Slack, or file-based).

## Available Operations

### Mutating Operations (Require Approval)

- `write_file` - Create/write files
- `edit_file` - Edit file content
- `create_directory` - Create directories
- `move_file` - Move/rename files
- `delete_file` - Delete files
- `delete_directory` - Delete directories

### Non-Mutating Operations (Immediate)

- `read_text_file` - Read file content
- `read_media_file` - Read media files
- `list_directory` - List directory contents
- `get_file_info` - Get file metadata
- `search_files` - Search for files

## Troubleshooting

If tests don't work as expected, check:
- [Claude Desktop Setup](claude-desktop-setup.md) - Verify configuration
- [Approval Methods](approval-methods.md) - Ensure approval methods are configured correctly
- Claude Desktop logs for error messages
