"""Desktop-control tools: launch/close apps, mouse, keyboard, clipboard.

``pyautogui`` and ``pyperclip`` are optional and require a display / clipboard
backend. When unavailable each tool returns a descriptive failure so the agent
can adapt rather than pretend an action succeeded.
"""

from __future__ import annotations

import platform
import shutil
import subprocess

from tools.base import Tool, ToolContext, ToolResult, tool

IS_WINDOWS = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"

try:
    import pyautogui

    pyautogui.FAILSAFE = False
except Exception:  # pragma: no cover - optional / needs display
    pyautogui = None  # type: ignore[assignment]

try:
    import pyperclip
except Exception:  # pragma: no cover
    pyperclip = None  # type: ignore[assignment]


def _need_gui() -> ToolResult | None:
    if pyautogui is None:
        return ToolResult.failure("pyautogui unavailable (no display / not installed).")
    return None


@tool(
    "open_application",
    "Launch an application by name or executable path.",
    {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
    category="desktop",
)
def open_application(ctx: ToolContext, name: str) -> ToolResult:
    try:
        if IS_WINDOWS:
            subprocess.Popen(["cmd", "/c", "start", "", name], shell=False)
        elif IS_MAC:
            subprocess.Popen(["open", "-a", name])
        else:
            exe = shutil.which(name) or name
            subprocess.Popen([exe])
    except Exception as exc:  # noqa: BLE001
        return ToolResult.failure(f"Could not launch '{name}': {exc}")
    if ctx.memory is not None:
        ctx.memory.note_app_usage(name)
    return ToolResult.success(f"Launched {name}")


@tool(
    "close_application",
    "Terminate all processes matching an application name.",
    {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
    destructive=True,
    category="desktop",
)
def close_application(ctx: ToolContext, name: str) -> ToolResult:
    try:
        import psutil

        killed = 0
        for proc in psutil.process_iter(["name"]):
            pname = (proc.info.get("name") or "").lower()
            if name.lower() in pname:
                proc.terminate()
                killed += 1
        return ToolResult.success(f"Terminated {killed} process(es) matching '{name}'.")
    except Exception as exc:  # noqa: BLE001
        return ToolResult.failure(f"Could not close '{name}': {exc}")


@tool(
    "move_mouse",
    "Move the mouse cursor to absolute screen coordinates.",
    {
        "type": "object",
        "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}},
        "required": ["x", "y"],
    },
    category="desktop",
)
def move_mouse(ctx: ToolContext, x: int, y: int) -> ToolResult:
    if (err := _need_gui()) is not None:
        return err
    pyautogui.moveTo(x, y, duration=0.2)
    return ToolResult.success(f"Moved mouse to ({x}, {y}).")


@tool(
    "click",
    "Click the mouse at the given coordinates (or current position).",
    {
        "type": "object",
        "properties": {
            "x": {"type": "integer"},
            "y": {"type": "integer"},
            "button": {"type": "string", "enum": ["left", "right", "middle"], "default": "left"},
        },
    },
    category="desktop",
)
def click(ctx: ToolContext, x: int | None = None, y: int | None = None, button: str = "left") -> ToolResult:
    if (err := _need_gui()) is not None:
        return err
    pyautogui.click(x=x, y=y, button=button)
    return ToolResult.success(f"Clicked {button} at ({x}, {y}).")


@tool(
    "keyboard_shortcut",
    "Press a keyboard shortcut, e.g. ['ctrl','s'] or ['alt','tab'].",
    {
        "type": "object",
        "properties": {"keys": {"type": "array", "items": {"type": "string"}}},
        "required": ["keys"],
    },
    category="desktop",
)
def keyboard_shortcut(ctx: ToolContext, keys: list[str]) -> ToolResult:
    if (err := _need_gui()) is not None:
        return err
    pyautogui.hotkey(*keys)
    return ToolResult.success(f"Pressed {'+'.join(keys)}.")


@tool(
    "type_text",
    "Type a string of text via the keyboard.",
    {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
    category="desktop",
)
def type_text(ctx: ToolContext, text: str) -> ToolResult:
    if (err := _need_gui()) is not None:
        return err
    pyautogui.typewrite(text, interval=0.01)
    return ToolResult.success(f"Typed {len(text)} characters.")


@tool("read_clipboard", "Read the current clipboard text contents.", category="desktop")
def read_clipboard(ctx: ToolContext) -> ToolResult:
    if pyperclip is None:
        return ToolResult.failure("pyperclip unavailable.")
    try:
        return ToolResult.success(pyperclip.paste())
    except Exception as exc:  # noqa: BLE001
        return ToolResult.failure(f"Clipboard read failed: {exc}")


@tool(
    "write_clipboard",
    "Copy text to the clipboard.",
    {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
    category="desktop",
)
def write_clipboard(ctx: ToolContext, text: str) -> ToolResult:
    if pyperclip is None:
        return ToolResult.failure("pyperclip unavailable.")
    try:
        pyperclip.copy(text)
        return ToolResult.success("Copied to clipboard.")
    except Exception as exc:  # noqa: BLE001
        return ToolResult.failure(f"Clipboard write failed: {exc}")


def get_tools() -> list[Tool]:
    return [
        open_application,
        close_application,
        move_mouse,
        click,
        keyboard_shortcut,
        type_text,
        read_clipboard,
        write_clipboard,
    ]
