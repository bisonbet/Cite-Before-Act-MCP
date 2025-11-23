# CLAUDE.md - AI Assistant Guide for Cite-Before-Act MCP

This document provides comprehensive guidance for AI assistants (like Claude) working with the Cite-Before-Act MCP codebase. It covers architecture, conventions, workflows, and best practices.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Codebase Structure](#codebase-structure)
3. [Core Architecture](#core-architecture)
4. [Development Workflows](#development-workflows)
5. [Key Conventions](#key-conventions)
6. [Configuration System](#configuration-system)
7. [Testing and Quality](#testing-and-quality)
8. [Common Tasks](#common-tasks)
9. [Important Patterns](#important-patterns)
10. [Debugging](#debugging)

---

## Project Overview

**Purpose:** Cite-Before-Act MCP is a middleware proxy server that implements "human-in-the-loop" safety for MCP (Model Context Protocol) servers. It intercepts tool calls, detects mutating operations, generates human-readable previews, and requires explicit approval before execution.

**Key Capabilities:**
- Acts as a transparent proxy between MCP clients (Claude Desktop) and upstream MCP servers
- Detects mutating operations using multiple strategies (allowlist, blocklist, naming conventions, metadata)
- Generates natural language previews of what actions will do
- Supports multiple approval methods (native OS dialogs, Slack, file-based)
- Works with any MCP server regardless of implementation language

**Technology Stack:**
- **Python 3.10+** (required minimum version)
- **FastMCP** - MCP server framework and proxy capabilities
- **Pydantic** - Configuration and data validation
- **python-dotenv** - Environment variable management
- **slack-sdk** - Slack integration (optional)
- **Flask** - Webhook server for Slack buttons (optional)

**License:** AGPL-3.0

---

## Codebase Structure

```
cite-before-act-mcp/
├── cite_before_act/          # Core library code
│   ├── __init__.py          # Package initialization
│   ├── middleware.py        # Main middleware logic (intercepts tool calls)
│   ├── detection.py         # Multi-strategy mutating tool detection
│   ├── explain.py           # Natural language preview generation
│   ├── approval.py          # Approval workflow management
│   ├── local_approval.py    # Local approval (native dialogs + file-based)
│   ├── debug.py             # Debug logging utilities
│   └── slack/               # Slack integration
│       ├── __init__.py
│       ├── client.py        # Slack API client
│       └── handlers.py      # Webhook handlers for interactive buttons
│
├── server/                   # Standalone proxy server
│   ├── __init__.py
│   ├── main.py              # Entry point and CLI argument parsing
│   └── proxy.py             # FastMCP proxy implementation
│
├── config/                   # Configuration management
│   ├── __init__.py
│   └── settings.py          # Environment variable handling and Pydantic models
│
├── examples/                 # Usage examples
│   ├── library_usage.py     # Using as a Python library
│   ├── standalone_server.py # Running as standalone server
│   └── unified_webhook_server.py # Multi-platform webhook server (Slack, Webex, Teams)
│
├── docs/                     # Documentation
│   ├── installation.md
│   ├── configuration.md
│   ├── architecture.md
│   ├── detection.md
│   ├── approval-methods.md
│   ├── slack-setup.md
│   ├── development.md
│   ├── advanced-usage.md
│   ├── testing.md
│   ├── upstream-servers.md
│   ├── claude-desktop-setup.md
│   └── examples/
│       └── github-example.md
│
├── tests/                    # Test suite (if present)
│
├── .env.example              # Example environment variables
├── pyproject.toml            # Python project configuration
├── requirements.txt          # Python dependencies
├── setup_wizard.py           # Interactive setup wizard
└── README.md                 # User-facing documentation
```

### Key Directories

- **`cite_before_act/`** - Core library that can be imported and used independently
- **`server/`** - Standalone server implementation using FastMCP
- **`config/`** - Configuration management with two-tier system
- **`docs/`** - Comprehensive documentation for users
- **`examples/`** - Working code examples for various use cases

---

## Core Architecture

### Request Flow

#### Non-Mutating Operation (Read-Only)
```
Client → Proxy → Middleware → Detection (identifies as read-only) → Upstream Server → Response
```

#### Mutating Operation (Requires Approval)
```
Client → Proxy → Middleware → Detection (identifies as mutating)
                                ↓
                         Explain Engine (generates preview)
                                ↓
                         Approval Manager (coordinates approval)
                                ↓
                    Multi-Method Approval (Native Dialog + Slack + File)
                                ↓
                         User Approves/Rejects
                                ↓
                    (if approved) → Upstream Server → Response
                    (if rejected) → PermissionError → Client
```

### Core Components

#### 1. Middleware (`cite_before_act/middleware.py`)

**Purpose:** Intercepts all tool calls and orchestrates the approval workflow.

**Key Methods:**
- `call_tool(tool_name, arguments, tool_description, tool_schema)` - Main interception point
- `_call_upstream(tool_name, arguments)` - Forwards to upstream server

**Responsibilities:**
- Intercept tool calls before execution
- Coordinate with detection, explanation, and approval components
- Forward approved calls to upstream server
- Raise PermissionError for rejected calls

#### 2. Detection Engine (`cite_before_act/detection.py`)

**Purpose:** Identifies whether a tool is mutating or read-only using multiple strategies.

**Detection Strategies (in precedence order):**
1. **Blocklist** (highest priority) - Explicit non-mutating tools
2. **Allowlist** (high priority) - Explicit mutating tools
3. **Convention-based** - Naming patterns (prefixes/suffixes)
4. **Metadata-based** - Description keyword analysis
5. **Read-only detection** - Read-only patterns (get_, read_, list_, etc.)
6. **Default** - Non-mutating (safe default)

**Key Patterns:**
- **Mutating prefixes:** `write_`, `delete_`, `create_`, `send_`, `update_`, `post_`, `charge_`, etc.
- **Read-only prefixes:** `get_`, `read_`, `list_`, `search_`, `find_`, `query_`, `fetch_`, etc.
- **Mutating keywords:** delete, create, modify, send, email, charge, payment, etc.
- **Read-only keywords:** read, get, list, search, view, display, status, etc.

**Important:** Detection uses word boundaries for metadata to avoid false positives (e.g., "account" won't match "count").

#### 3. Explain Engine (`cite_before_act/explain.py`)

**Purpose:** Generates human-readable previews of tool actions.

**Responsibilities:**
- Extract key information from tool arguments
- Format natural language descriptions
- Keep previews concise but informative
- Handle various argument types (strings, objects, arrays)

**Example Preview:**
```
Write file: /path/to/file.txt (1,234 bytes)
```

#### 4. Approval Manager (`cite_before_act/approval.py`)

**Purpose:** Coordinates multiple approval methods and manages approval state.

**Approval Methods:**
- **Native OS Dialogs** (macOS/Windows via osascript/PowerShell)
- **Slack** (messages with interactive buttons)
- **File-based** (writes JSON to /tmp for CLI approval)

**Key Features:**
- Runs multiple approval methods concurrently
- Handles timeouts (default 300 seconds)
- Manages approval state (pending/approved/rejected/timeout)
- Auto-disables native dialogs when Slack is enabled

#### 5. Proxy Server (`server/proxy.py`)

**Purpose:** FastMCP-based proxy that wraps upstream MCP servers.

**Supported Transports:**
- **stdio** - Standard input/output (default for Claude Desktop)
- **HTTP** - REST API communication
- **SSE** - Server-Sent Events (for streaming)

**Responsibilities:**
- Initialize FastMCP server
- Connect to upstream MCP server
- Route tool calls through middleware
- Handle MCP protocol communication

---

## Development Workflows

### Initial Setup

```bash
# Clone repository
git clone https://github.com/bisonbet/Cite-Before-Act-MCP.git
cd Cite-Before-Act-MCP

# Install development dependencies
pip install -e ".[dev]"

# Create .env file
cp .env.example .env
# Edit .env and add your tokens if needed
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=cite_before_act --cov-report=html

# Run specific test file
pytest tests/test_detection.py

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Format code (always run before committing)
black .

# Lint code
ruff check .

# Fix linting issues automatically
ruff check --fix .

# Type checking
mypy cite_before_act/
```

### Commit Conventions

Use conventional commit messages:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `refactor:` - Code refactoring
- `test:` - Test changes
- `chore:` - Maintenance tasks

**Example:**
```bash
git commit -m "feat: add support for custom detection patterns"
git commit -m "fix: handle timeout errors in approval manager"
git commit -m "docs: update configuration guide with new options"
```

---

## Key Conventions

### Code Style

- **PEP 8 compliance** - Follow Python style guidelines
- **Type hints** - Use type hints for all function signatures
- **Docstrings** - Write comprehensive docstrings for public functions/classes
- **Line length** - Maximum 100 characters (configured in pyproject.toml)
- **Naming:**
  - Classes: `PascalCase` (e.g., `DetectionEngine`)
  - Functions/methods: `snake_case` (e.g., `is_mutating`)
  - Constants: `UPPER_SNAKE_CASE` (e.g., `READ_ONLY_PREFIXES`)
  - Private methods: `_leading_underscore` (e.g., `_check_convention`)

### Docstring Format

```python
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
```

### Error Handling

- **Mutating tools rejected:** Raise `PermissionError` with descriptive message
- **Configuration errors:** Raise at startup with clear guidance
- **Upstream errors:** Propagate to client with context
- **Timeout errors:** Return timeout status in approval response

### Async Patterns

- Use `async/await` for I/O operations
- Middleware supports both sync and async upstream functions
- Approval manager uses `asyncio.create_task()` for concurrent approvals

---

## Configuration System

### Two-Tier Architecture

Cite-Before-Act uses a **two-tier configuration system** that separates concerns:

#### Tier 1: `.env` File (Global Defaults and Secrets)

**Location:** Project root directory

**Purpose:** Store secrets and global settings that apply to ALL wrapped MCP servers

**Contains:**
- Secrets: `GITHUB_PERSONAL_ACCESS_TOKEN`, `SLACK_BOT_TOKEN`
- Global settings: `ENABLE_SLACK`, `USE_LOCAL_APPROVAL`, `APPROVAL_TIMEOUT_SECONDS`
- Detection defaults: `DETECTION_ENABLE_CONVENTION`, `DETECTION_ENABLE_METADATA`

**Example:**
```bash
# Secrets
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_your_token
SLACK_BOT_TOKEN=xoxb-your-token

# Global settings
ENABLE_SLACK=true
SLACK_CHANNEL=#approvals
APPROVAL_TIMEOUT_SECONDS=300
USE_GUI_APPROVAL=false
```

#### Tier 2: Claude Desktop Config (Per-Server Settings)

**Location:** `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)

**Purpose:** Configure each individual upstream MCP server

**Contains:**
- Server-specific: `UPSTREAM_COMMAND`, `UPSTREAM_ARGS`, `UPSTREAM_TRANSPORT`, `UPSTREAM_URL`
- Per-server detection: `DETECTION_ALLOWLIST`, `DETECTION_BLOCKLIST`
- Optional overrides: Can override global settings if needed

**Example:**
```json
{
  "mcpServers": {
    "github-cite": {
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "server.main", "--transport", "stdio"],
      "env": {
        "UPSTREAM_COMMAND": "docker",
        "UPSTREAM_ARGS": "run,-i,--rm,ghcr.io/github/github-mcp-server",
        "UPSTREAM_TRANSPORT": "stdio",
        "DETECTION_BLOCKLIST": "read_file,get_file,search_code"
      }
    }
  }
}
```

### Environment Variable Precedence

**Priority order:**
1. **mcpServers.env** (highest) - Per-server overrides in Claude Desktop config
2. **.env file** (lower) - Global defaults and secrets

### Configuration Loading (`config/settings.py`)

- Uses `python-dotenv` to load `.env` file
- Loads from absolute path (project root) - works regardless of launch directory
- `load_dotenv()` does NOT override existing environment variables
- Claude Desktop sets `mcpServers.env` vars first, then `.env` fills in the rest

**Key Classes:**
- `Settings` - Main configuration model (Pydantic)
- `SlackConfig` - Slack-specific settings
- `DetectionConfig` - Detection engine settings
- `UpstreamServerConfig` - Upstream server connection settings

---

## Testing and Quality

### Test Organization

- Tests should mirror the source code structure
- Use `pytest` fixtures for common setup
- Test both success and error cases
- Maintain or improve code coverage

### Test Categories

1. **Unit Tests** - Test individual components in isolation
2. **Integration Tests** - Test component interactions
3. **End-to-End Tests** - Test full workflow from client to upstream

### Quality Standards

- **Code coverage:** Maintain or improve existing coverage
- **Type checking:** All public APIs must have type hints
- **Documentation:** All public functions must have docstrings
- **Linting:** Code must pass `ruff check` without errors
- **Formatting:** Code must be formatted with `black`

### Pre-Commit Checklist

```bash
# 1. Run tests
pytest

# 2. Format code
black .

# 3. Check linting
ruff check .

# 4. Check types
mypy cite_before_act/

# 5. Commit with conventional message
git commit -m "feat: your change description"
```

---

## Common Tasks

### Adding a New Detection Pattern

**File:** `cite_before_act/detection.py`

1. Add pattern to appropriate set:
   - `MUTATING_PREFIXES` / `MUTATING_SUFFIXES` / `MUTATING_KEYWORDS`
   - `READ_ONLY_PREFIXES` / `READ_ONLY_SUFFIXES` / `READ_ONLY_KEYWORDS`

2. Test the pattern:
```python
# In tests/test_detection.py
def test_new_pattern():
    engine = DetectionEngine(enable_convention=True)
    assert engine.is_mutating("your_new_pattern") == True  # or False
```

3. Update documentation in `docs/detection.md`

### Adding a New Approval Method

**File:** `cite_before_act/approval.py`

1. Create new approval method in `ApprovalManager`
2. Add to concurrent approval tasks in `request_approval()`
3. Handle method-specific errors gracefully
4. Update `docs/approval-methods.md`

### Supporting a New Upstream Transport

**File:** `server/proxy.py`

1. Add transport option to `ProxyServer.__init__()`
2. Implement connection logic in `_connect_upstream()`
3. Update CLI arguments in `server/main.py`
4. Document in `docs/configuration.md`

### Adding a New Configuration Option

**Files:** `config/settings.py`, `.env.example`

1. Add field to appropriate Pydantic model in `settings.py`:
```python
class Settings(BaseModel):
    new_option: bool = Field(True, description="Description")
```

2. Update `Settings.from_env()` to load from environment:
```python
new_option = os.getenv("NEW_OPTION", "true").lower() == "true"
```

3. Add to `.env.example` with documentation
4. Update `docs/configuration.md`

### Debugging Tool Detection

Enable debug logging to see detection decisions:

```bash
# In .env or Claude Desktop config
DEBUG=true
```

This logs:
- Which detection strategies matched
- Tool names and descriptions analyzed
- Final mutating/non-mutating decision

**Example debug output:**
```
[DEBUG] Middleware intercepting tool call: 'create_repository'
[DEBUG] Tool 'create_repository' detected as mutating via convention (prefix/suffix)
[DEBUG] Tool 'create_repository' is_mutating=True
```

---

## Important Patterns

### 1. Security-First Detection

**Pattern:** When in doubt, require approval.

```python
# Check mutating patterns FIRST
if is_mutating_by_convention or is_mutating_by_metadata:
    return True  # Require approval

# Only then check read-only patterns
if self._check_read_only(...):
    return False  # Allow without approval

# Default: non-mutating (but could be configurable)
return False
```

**Rationale:** It's safer to ask for unnecessary approval than to execute a mutating operation without permission.

### 2. Dual Sync/Async Support

**Pattern:** Support both sync and async upstream functions.

```python
# In middleware.py
result = self.upstream_tool_call(tool_name, arguments)
if hasattr(result, "__await__"):
    return await result
return result
```

**Rationale:** Upstream MCP servers may be sync or async; the middleware must handle both.

### 3. Concurrent Approval Methods

**Pattern:** Run multiple approval methods concurrently, accept first response.

```python
# In approval.py
tasks = []
if self.use_slack:
    tasks.append(self._slack_approval(...))
if self.use_local:
    tasks.append(self._local_approval(...))

# Wait for first approval response
done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
```

**Rationale:** User can respond via any method; first response wins.

### 4. Graceful Fallbacks

**Pattern:** Fall back to safer options when preferred methods fail.

```python
# Slack enabled? Disable native dialogs (avoid duplicate popups)
if self.enable_slack and self.slack_config:
    self.use_gui_approval = False

# Always enable file-based approval as ultimate fallback
# (logs instructions regardless of other methods)
```

**Rationale:** Ensure users always have a way to approve/reject, even if some methods fail.

### 5. Absolute Path Configuration

**Pattern:** Use absolute paths to find configuration files.

```python
# In config/settings.py
_project_root = Path(__file__).parent.parent
_env_path = _project_root / ".env"
load_dotenv(_env_path)
```

**Rationale:** MCP clients may launch the server from any directory; absolute paths ensure `.env` is always found.

---

## Debugging

### Debug Logging

Enable with `DEBUG=true` environment variable.

**What gets logged:**
- Tool detection decisions and matched strategies
- Middleware interception and routing
- Upstream communication (arguments and responses)
- Schema information and parameter validation

**Where logs appear:**
- Written to `stderr`
- Visible in Claude Desktop's MCP logs
- Does not affect normal operation when disabled

### Common Issues

#### 1. Tool Not Detected as Mutating

**Debug steps:**
1. Enable `DEBUG=true`
2. Check detection logs: which strategies ran?
3. Verify tool name/description
4. Add to `DETECTION_ALLOWLIST` if needed

#### 2. Upstream Connection Fails

**Debug steps:**
1. Check `UPSTREAM_COMMAND` / `UPSTREAM_URL` is correct
2. Test upstream server independently
3. Verify transport type matches upstream
4. Check authentication headers for remote servers

#### 3. Approval Timeout

**Debug steps:**
1. Increase `APPROVAL_TIMEOUT_SECONDS` if needed
2. Check approval method is working (Slack messages sent? Native dialog appeared?)
3. Verify file-based approval instructions in logs
4. Check user has permission to respond

#### 4. Configuration Not Loading

**Debug steps:**
1. Verify `.env` exists in project root
2. Check environment variable names (exact match required)
3. Verify precedence (Claude Desktop config overrides `.env`)
4. Check for typos in variable names

### Useful Debug Commands

```bash
# Test detection engine standalone
python -c "
from cite_before_act.detection import DetectionEngine
engine = DetectionEngine(enable_convention=True)
print(engine.is_mutating('write_file'))  # Should be True
print(engine.is_mutating('read_file'))   # Should be False
"

# Check environment variables
python -c "
from config.settings import get_settings
settings = get_settings()
print(f'Upstream: {settings.upstream}')
print(f'Slack: {settings.slack}')
"

# Test upstream connection
python -m server.main --transport stdio
# Then interact via stdin/stdout
```

---

## Working with This Codebase as an AI Assistant

### When Making Changes

1. **Read existing code first** - Understand patterns before modifying
2. **Maintain consistency** - Follow existing conventions
3. **Update tests** - Add/modify tests for changed functionality
4. **Update documentation** - Keep docs in sync with code
5. **Run quality checks** - Format, lint, type-check before committing

### When Adding Features

1. **Check related files** - Similar features may exist elsewhere
2. **Consider configuration** - Should it be configurable? Global or per-server?
3. **Think about security** - Does it affect mutating tool detection?
4. **Plan approval flow** - Does it need user approval?
5. **Document thoroughly** - Update relevant docs in `docs/`

### When Debugging Issues

1. **Enable debug logging first** - See what's actually happening
2. **Check configuration precedence** - `.env` vs Claude Desktop config
3. **Verify detection logic** - Is the tool being detected correctly?
4. **Test upstream independently** - Isolate proxy from upstream issues
5. **Read existing docs** - Answer may be in `docs/`

### File Reference Quick Guide

| Task | Primary File(s) |
|------|----------------|
| Detection logic | `cite_before_act/detection.py` |
| Approval workflow | `cite_before_act/approval.py` |
| Preview generation | `cite_before_act/explain.py` |
| Middleware interception | `cite_before_act/middleware.py` |
| Configuration management | `config/settings.py` |
| Proxy server | `server/proxy.py`, `server/main.py` |
| Slack integration | `cite_before_act/slack/` |
| Environment variables | `.env.example` |
| User documentation | `docs/*.md` |
| Examples | `examples/*.py` |

### Documentation Locations

| Topic | File |
|-------|------|
| Installation | `docs/installation.md` |
| Configuration | `docs/configuration.md` |
| Detection system | `docs/detection.md` |
| Approval methods | `docs/approval-methods.md` |
| Architecture | `docs/architecture.md` |
| Development | `docs/development.md` |
| Slack setup | `docs/slack-setup.md` |
| Testing | `docs/testing.md` |
| Advanced usage | `docs/advanced-usage.md` |

---

## Summary

Cite-Before-Act MCP is a well-structured Python project that acts as a safety middleware for MCP servers. The codebase follows clean architecture principles with clear separation of concerns:

- **Detection** identifies mutating operations
- **Explanation** generates human-readable previews
- **Approval** coordinates user consent
- **Middleware** orchestrates the workflow
- **Proxy** handles MCP protocol communication

The two-tier configuration system elegantly separates secrets (`.env`) from per-server settings (Claude Desktop config), enabling multi-server deployments with shared credentials.

When working with this codebase, prioritize security (err on the side of requiring approval), maintain consistency with existing patterns, and keep documentation synchronized with code changes.

For detailed information on specific topics, refer to the comprehensive documentation in the `docs/` directory.

---

**Last Updated:** 2024-11-18
**For Questions:** See `docs/development.md` or open an issue on GitHub
