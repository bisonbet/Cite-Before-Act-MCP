"""Cite-Before-Act MCP - Middleware for requiring approval on state-mutating tool calls."""

__version__ = "0.1.0"

from cite_before_act.middleware import Middleware
from cite_before_act.detection import DetectionEngine
from cite_before_act.explain import ExplainEngine
from cite_before_act.approval import ApprovalManager
from cite_before_act.local_approval import LocalApproval

__all__ = [
    "Middleware",
    "DetectionEngine",
    "ExplainEngine",
    "ApprovalManager",
    "LocalApproval",
]

