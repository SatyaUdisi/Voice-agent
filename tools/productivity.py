"""Productivity tools: notes, todos, reminders, timers, calculator.

Notes / todos / reminders persist through the preferences + memory tables so
they survive restarts. Timers and the stopwatch are lightweight in-process
helpers suitable for a desktop assistant.
"""

from __future__ import annotations

import ast
import json
import operator
import threading
import time
from collections.abc import Callable
from datetime import datetime, timedelta

from tools.base import Tool, ToolContext, ToolResult, tool

# ---- Safe arithmetic evaluator (no builtins / names) ---------------------- #
_BIN_OPS: dict[type, Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}
_UNARY_OPS: dict[type, Callable[[float], float]] = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _safe_eval(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        return _BIN_OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("Unsupported expression")


def _load_list(ctx: ToolContext, key: str) -> list[str]:
    if ctx.memory is None:
        return []
    raw = ctx.memory.get_preference(key, "[]")
    try:
        return list(json.loads(raw or "[]"))
    except json.JSONDecodeError:
        return []


def _save_list(ctx: ToolContext, key: str, items: list[str]) -> None:
    if ctx.memory is not None:
        ctx.memory.set_preference(key, json.dumps(items))


@tool(
    "calculator",
    "Evaluate a basic arithmetic expression (e.g. '3*(4+5)/2').",
    {"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]},
    category="productivity",
)
def calculator(ctx: ToolContext, expression: str) -> ToolResult:
    try:
        value = _safe_eval(ast.parse(expression, mode="eval"))
    except Exception as exc:  # noqa: BLE001
        return ToolResult.failure(f"Cannot evaluate '{expression}': {exc}")
    return ToolResult.success(str(value), value=value)


@tool(
    "add_note",
    "Save a text note.",
    {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
    category="productivity",
)
def add_note(ctx: ToolContext, text: str) -> ToolResult:
    notes = _load_list(ctx, "notes")
    notes.append(f"{datetime.now():%Y-%m-%d %H:%M} | {text}")
    _save_list(ctx, "notes", notes)
    return ToolResult.success(f"Note saved ({len(notes)} total).")


@tool("list_notes", "List all saved notes.", category="productivity")
def list_notes(ctx: ToolContext) -> ToolResult:
    notes = _load_list(ctx, "notes")
    return ToolResult.success("\n".join(notes) or "(no notes)", notes=notes)


@tool(
    "add_todo",
    "Add an item to the to-do list.",
    {"type": "object", "properties": {"item": {"type": "string"}}, "required": ["item"]},
    category="productivity",
)
def add_todo(ctx: ToolContext, item: str) -> ToolResult:
    todos = _load_list(ctx, "todos")
    todos.append(item)
    _save_list(ctx, "todos", todos)
    return ToolResult.success(f"Added to-do ({len(todos)} open).")


@tool("list_todos", "List all open to-do items.", category="productivity")
def list_todos(ctx: ToolContext) -> ToolResult:
    todos = _load_list(ctx, "todos")
    listing = "\n".join(f"{i+1}. {t}" for i, t in enumerate(todos))
    return ToolResult.success(listing or "(no to-dos)", todos=todos)


@tool(
    "complete_todo",
    "Complete/remove a to-do by its 1-based index.",
    {"type": "object", "properties": {"index": {"type": "integer"}}, "required": ["index"]},
    category="productivity",
)
def complete_todo(ctx: ToolContext, index: int) -> ToolResult:
    todos = _load_list(ctx, "todos")
    if not 1 <= index <= len(todos):
        return ToolResult.failure(f"Index out of range (1-{len(todos)}).")
    done = todos.pop(index - 1)
    _save_list(ctx, "todos", todos)
    return ToolResult.success(f"Completed: {done}")


@tool(
    "add_reminder",
    "Store a reminder with an ISO date/time and message.",
    {
        "type": "object",
        "properties": {"when": {"type": "string"}, "message": {"type": "string"}},
        "required": ["when", "message"],
    },
    category="productivity",
)
def add_reminder(ctx: ToolContext, when: str, message: str) -> ToolResult:
    reminders = _load_list(ctx, "reminders")
    reminders.append(f"{when} | {message}")
    _save_list(ctx, "reminders", reminders)
    return ToolResult.success(f"Reminder set for {when}.")


@tool(
    "start_timer",
    "Start a countdown timer (seconds). Fires a log entry when it elapses.",
    {"type": "object", "properties": {"seconds": {"type": "integer"}}, "required": ["seconds"]},
    category="productivity",
)
def start_timer(ctx: ToolContext, seconds: int) -> ToolResult:
    from logs import LogCategory, log_event

    def _fire() -> None:
        log_event(LogCategory.SYSTEM, "timer_elapsed", seconds=seconds)

    timer = threading.Timer(max(0, seconds), _fire)
    timer.daemon = True
    timer.start()
    eta = (datetime.now() + timedelta(seconds=seconds)).strftime("%H:%M:%S")
    return ToolResult.success(f"Timer started for {seconds}s (fires ~{eta}).")


# Simple in-process stopwatch keyed by name.
_STOPWATCHES: dict[str, float] = {}


@tool(
    "stopwatch",
    "Control a named stopwatch. action = start | stop.",
    {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["start", "stop"]},
            "name": {"type": "string", "default": "default"},
        },
        "required": ["action"],
    },
    category="productivity",
)
def stopwatch(ctx: ToolContext, action: str, name: str = "default") -> ToolResult:
    if action == "start":
        _STOPWATCHES[name] = time.perf_counter()
        return ToolResult.success(f"Stopwatch '{name}' started.")
    start = _STOPWATCHES.pop(name, None)
    if start is None:
        return ToolResult.failure(f"No running stopwatch named '{name}'.")
    elapsed = time.perf_counter() - start
    return ToolResult.success(f"Stopwatch '{name}': {elapsed:.2f}s", elapsed=elapsed)


def get_tools() -> list[Tool]:
    return [
        calculator,
        add_note,
        list_notes,
        add_todo,
        list_todos,
        complete_todo,
        add_reminder,
        start_timer,
        stopwatch,
    ]
