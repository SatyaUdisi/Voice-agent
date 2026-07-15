"""Core tool abstractions: :class:`Tool`, :class:`ToolRegistry`, results.

Design goals:
* A tool is a pure, self-describing unit (name, description, JSON schema, handler).
* The registry turns tools into OpenAI function-calling schemas and dispatches
  calls, capturing timing + errors so the agent can *verify* execution instead
  of hallucinating success.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from logs import LogCategory, log_event


@dataclass(slots=True)
class ToolContext:
    """Shared services handed to every tool at execution time.

    Attributes are optional so tools remain testable in isolation.
    """

    settings: Any = None
    memory: Any = None
    confirm: Callable[[str], bool] | None = None


@dataclass(slots=True)
class ToolResult:
    """The outcome of a tool invocation.

    ``ok`` lets the agent verify a task actually completed. ``output`` is a
    concise, model-friendly summary; ``data`` carries structured details.
    """

    ok: bool
    output: str
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    @classmethod
    def success(cls, output: str, **data: Any) -> ToolResult:
        return cls(ok=True, output=output, data=data)

    @classmethod
    def failure(cls, error: str, **data: Any) -> ToolResult:
        return cls(ok=False, output=error, data=data, error=error)


# Handler signature: (context, **kwargs) -> ToolResult
ToolHandler = Callable[..., ToolResult]


@dataclass(slots=True)
class Tool:
    """A single callable capability exposed to the agent."""

    name: str
    description: str
    parameters: dict[str, Any]
    handler: ToolHandler
    destructive: bool = False
    category: str = "general"

    def to_openai_schema(self) -> dict[str, Any]:
        """Render this tool as an OpenAI ``tools`` entry."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


def tool(
    name: str,
    description: str,
    parameters: dict[str, Any] | None = None,
    *,
    destructive: bool = False,
    category: str = "general",
) -> Callable[[ToolHandler], Tool]:
    """Decorator that turns a handler function into a :class:`Tool`."""

    def wrap(func: ToolHandler) -> Tool:
        return Tool(
            name=name,
            description=description,
            parameters=parameters or {"type": "object", "properties": {}},
            handler=func,
            destructive=destructive,
            category=category,
        )

    return wrap


class ToolRegistry:
    """Holds tools and dispatches calls with logging + confirmation."""

    def __init__(self, context: ToolContext | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        self._context = context or ToolContext()

    @property
    def context(self) -> ToolContext:
        return self._context

    def register(self, *tools: Tool) -> None:
        for t in tools:
            if t.name in self._tools:
                raise ValueError(f"Duplicate tool name: {t.name}")
            self._tools[t.name] = t

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def all(self) -> list[Tool]:
        return list(self._tools.values())

    def openai_schemas(self) -> list[dict[str, Any]]:
        return [t.to_openai_schema() for t in self._tools.values()]

    def call(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        """Execute a tool by name, capturing latency, errors and confirmation."""
        tool_obj = self._tools.get(name)
        if tool_obj is None:
            return ToolResult.failure(f"Unknown tool: {name}")

        # Destructive tools may require explicit confirmation.
        if tool_obj.destructive and self._context.confirm is not None:
            if not self._context.confirm(f"Allow '{name}' with {arguments}?"):
                return ToolResult.failure(f"User declined execution of '{name}'.")

        start = time.perf_counter()
        try:
            result = tool_obj.handler(self._context, **arguments)
        except TypeError as exc:
            result = ToolResult.failure(f"Bad arguments for '{name}': {exc}")
        except Exception as exc:  # noqa: BLE001 - surface any tool failure to the agent
            result = ToolResult.failure(f"{type(exc).__name__}: {exc}")
        elapsed_ms = (time.perf_counter() - start) * 1000

        log_event(
            LogCategory.TOOL_CALL,
            f"tool:{name}",
            arguments=arguments,
            ok=result.ok,
            error=result.error,
        )
        log_event(LogCategory.LATENCY, f"tool:{name}", elapsed_ms=round(elapsed_ms, 2))
        return result
