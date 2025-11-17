# Advanced Usage

This guide covers advanced usage patterns for Cite-Before-Act MCP.

## As a Library

You can use Cite-Before-Act as a Python library in your own projects:

```python
from cite_before_act import DetectionEngine, ExplainEngine, ApprovalManager, Middleware
from cite_before_act.slack import SlackClient

# Initialize components
detection = DetectionEngine(allowlist=["write_file", "delete_file"])
explain = ExplainEngine()
slack_client = SlackClient(token="xoxb-...", channel="#approvals")
approval_manager = ApprovalManager(slack_client=slack_client)

middleware = Middleware(
    detection_engine=detection,
    explain_engine=explain,
    approval_manager=approval_manager,
    upstream_tool_call=your_tool_call_function,
)

# Intercept tool calls
result = await middleware.call_tool(
    tool_name="write_file",
    arguments={"path": "/tmp/test.txt", "content": "Hello"},
)
```

See `examples/library_usage.py` for complete examples.

## Standalone Server

Run the proxy server directly without Claude Desktop:

### stdio Transport (Default)

```bash
python -m server.main --transport stdio
```

This mode is designed for integration with MCP clients that communicate via standard input/output.

### HTTP Transport

```bash
python -m server.main --transport http --host 0.0.0.0 --port 8000
```

Access the server at `http://localhost:8000`

### SSE Transport (Server-Sent Events)

```bash
python -m server.main --transport sse --host 0.0.0.0 --port 8000
```

This mode is useful for modern MCP servers that support server-sent events.

## Custom Approval Methods

You can implement custom approval methods by extending the `ApprovalManager` class:

```python
from cite_before_act.approval import ApprovalManager

class CustomApprovalManager(ApprovalManager):
    async def request_approval(self, preview: str, approval_id: str) -> bool:
        # Your custom approval logic here
        # Return True for approved, False for rejected
        pass
```

## Custom Detection Strategies

Implement custom detection logic by extending `DetectionEngine`:

```python
from cite_before_act.detection import DetectionEngine

class CustomDetectionEngine(DetectionEngine):
    def is_mutating(self, tool_name: str, tool_schema: dict) -> bool:
        # Your custom detection logic
        if self._custom_check(tool_name):
            return True
        return super().is_mutating(tool_name, tool_schema)

    def _custom_check(self, tool_name: str) -> bool:
        # Custom detection rules
        return tool_name.startswith("dangerous_")
```

## Integration Examples

### Flask Web Application

```python
from flask import Flask, request
from cite_before_act import Middleware

app = Flask(__name__)
middleware = Middleware(...)  # Initialize middleware

@app.route('/tool-call', methods=['POST'])
async def handle_tool_call():
    data = request.json
    result = await middleware.call_tool(
        tool_name=data['tool'],
        arguments=data['args']
    )
    return result
```

### FastAPI Application

```python
from fastapi import FastAPI
from cite_before_act import Middleware

app = FastAPI()
middleware = Middleware(...)  # Initialize middleware

@app.post("/tool-call")
async def handle_tool_call(tool: str, args: dict):
    result = await middleware.call_tool(
        tool_name=tool,
        arguments=args
    )
    return result
```

## Environment-Specific Configuration

You can use different configurations for different environments:

```bash
# Development
export DEBUG=true
export APPROVAL_TIMEOUT_SECONDS=600

# Production
export DEBUG=false
export APPROVAL_TIMEOUT_SECONDS=300
export SECURITY_MODE=production
```

## Next Steps

- [Architecture](architecture.md) - Understand the system architecture
- [Development](development.md) - Contributing to the project
