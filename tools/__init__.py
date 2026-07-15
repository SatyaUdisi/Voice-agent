"""Tool system: registry, schemas and built-in tool packs.

Tools are the only way the agent affects the outside world. Each tool declares
a JSON-schema for its parameters (consumed by OpenAI function calling), a
handler, and whether it is *destructive* (requiring confirmation).
"""

from tools.base import Tool, ToolContext, ToolRegistry, ToolResult, tool
from tools.registry import build_default_registry

__all__ = [
    "Tool",
    "ToolContext",
    "ToolRegistry",
    "ToolResult",
    "tool",
    "build_default_registry",
]
