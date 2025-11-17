# Detection System

The detection system identifies which tool calls require approval and which can execute immediately.

## Detection Strategies

Detection strategies are applied in priority order:

### 1. Blocklist (Highest Priority)

Explicitly listed tools never require approval:

```bash
DETECTION_BLOCKLIST=read_file,list_directory,get_info
```

### 2. Read-Only Detection

Automatically detects read-only operations (no approval needed):

**Prefixes:**
- `get_`, `read_`, `list_`, `search_`, `find_`, `query_`, `fetch_`, `retrieve_`, `show_`, `view_`, `describe_`, `info_`, `check_`, `verify_`

**Suffixes:**
- `_get`, `_read`, `_list`, `_search`, `_find`, `_query`, `_fetch`, `_show`, `_view`, `_info`

**Keywords in descriptions:**
- "read", "get", "list", "search", "find", "query", "fetch", "retrieve", "show", "view", "describe", "info", "status", "check", "verify", "read-only"

**Examples automatically allowed:**
- `search_repositories` → Detected via `search_` prefix
- `get_file` → Detected via `get_` prefix
- `list_issues` → Detected via `list_` prefix
- Any tool with description "searches for repositories" → Detected via "search" keyword

### 3. Allowlist (High Priority)

Explicitly listed tools always require approval:

```bash
DETECTION_ALLOWLIST=write_file,edit_file,create_directory,move_file
```

**Important:** The allowlist is **additive**, not exclusive. Convention and metadata detection still work for all tools not in the allowlist.

### 4. Convention-Based Detection (Mutating)

Automatically detects tools with mutating prefixes/suffixes:

**File/resource operations:**
- `write_`, `delete_`, `remove_`, `create_`, `update_`, `edit_`, `modify_`, `move_`, `copy_`

**Communication operations:**
- `send_`, `email_`, `message_`, `tweet_`, `post_`, `share_`, `publish_`, `notify_`, `broadcast_`, `dm_`, `sms_`

**Payment/transaction operations:**
- `charge_`, `payment_`, `transaction_`, `purchase_`, `refund_`

**HTTP/API operations:**
- `put_`, `patch_`

**Suffixes:**
- `_delete`, `_remove`, `_write`, `_create`, `_send`, `_email`, `_tweet`, `_charge`

**Examples automatically detected:**
- `send_email` → Detected via `send_` prefix
- `post_tweet` → Detected via `post_` prefix
- `charge_payment` → Detected via `charge_` prefix

### 5. Metadata-Based Detection (Mutating)

Analyzes tool descriptions for keywords:

**File operations:**
- "delete", "remove", "create", "write", "modify", "update"

**Communication:**
- "send", "email", "message", "tweet", "post", "share", "publish", "notify", "broadcast", "dm", "sms", "social media"

**Payments:**
- "charge", "payment", "transaction", "purchase", "refund", "bill", "invoice"

**Examples:**
- Tool with description "sends an email message" → Detected via "send" and "email" keywords
- Tool with description "posts content to social media" → Detected via "post" and "social media" keywords

## Configuration

### Global Detection Settings (`.env` file)

Enable/disable detection strategies globally:

```bash
DETECTION_ENABLE_CONVENTION=true   # Detect by naming patterns
DETECTION_ENABLE_METADATA=true     # Detect by description keywords
```

### Per-Server Overrides (Claude Desktop config)

Override detection for specific tools on each server:

```bash
# In mcpServers.env
DETECTION_ALLOWLIST=write_file,edit_file    # Always require approval
DETECTION_BLOCKLIST=read_file,list_dir      # Never require approval
```

## Why This Approach?

The multi-strategy detection system ensures:

1. **Automatic coverage** - Most mutating operations are detected without configuration
2. **Flexibility** - Override detection per-server as needed
3. **Safety** - Blocklist provides explicit control over critical tools
4. **Convenience** - Read-only operations flow smoothly without interruption

You don't need to enumerate every possible mutating tool - the convention and metadata detection catch them automatically.

## Examples

### Read-Only (No Approval Required)

```
search_repositories   → search_ prefix
get_file             → get_ prefix
list_issues          → list_ prefix
find_user            → find_ prefix
query_database       → query_ prefix
```

### Mutating (Requires Approval)

```
write_file           → write_ prefix
delete_repository    → delete_ prefix
send_email           → send_ prefix
post_tweet           → post_ prefix
charge_payment       → charge_ prefix
create_issue         → create_ prefix
update_settings      → update_ prefix
```

## Next Steps

- [Configuration Reference](configuration.md) - Detailed configuration options
- [Testing](testing.md) - Verify detection works correctly
