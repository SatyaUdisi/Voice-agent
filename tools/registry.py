"""Assemble the default :class:`ToolRegistry` from all built-in tool packs."""

from __future__ import annotations

from tools import browser, coding, desktop, files, productivity, system, vision
from tools.base import ToolContext, ToolRegistry


def build_default_registry(context: ToolContext | None = None) -> ToolRegistry:
    """Create a registry populated with every built-in tool.

    Args:
        context: Shared :class:`ToolContext` (settings, memory, confirm callback).
    """
    registry = ToolRegistry(context)
    for pack in (files, system, desktop, browser, productivity, coding, vision):
        registry.register(*pack.get_tools())
    return registry
