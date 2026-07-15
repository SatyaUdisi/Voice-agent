"""File-management tools. Fully cross-platform (pure stdlib)."""

from __future__ import annotations

import shutil
from pathlib import Path

from tools.base import Tool, ToolContext, ToolResult, tool

_PATH_ARG = {"type": "string", "description": "Filesystem path."}


@tool(
    "create_file",
    "Create a new text file (and parent folders), optionally with content.",
    {
        "type": "object",
        "properties": {
            "path": _PATH_ARG,
            "content": {"type": "string", "description": "Text to write.", "default": ""},
        },
        "required": ["path"],
    },
    category="files",
)
def create_file(ctx: ToolContext, path: str, content: str = "") -> ToolResult:
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    if not target.exists():  # verify
        return ToolResult.failure(f"File was not created: {target}")
    return ToolResult.success(f"Created {target} ({target.stat().st_size} bytes)", path=str(target))


@tool(
    "create_folder",
    "Create a folder (and any missing parents).",
    {"type": "object", "properties": {"path": _PATH_ARG}, "required": ["path"]},
    category="files",
)
def create_folder(ctx: ToolContext, path: str) -> ToolResult:
    target = Path(path).expanduser()
    target.mkdir(parents=True, exist_ok=True)
    if ctx.memory is not None:
        ctx.memory.note_folder_usage(str(target))
    return ToolResult.success(f"Folder ready: {target}", path=str(target))


@tool(
    "read_file",
    "Read a UTF-8 text file and return its contents.",
    {
        "type": "object",
        "properties": {
            "path": _PATH_ARG,
            "max_chars": {"type": "integer", "default": 10000},
        },
        "required": ["path"],
    },
    category="files",
)
def read_file(ctx: ToolContext, path: str, max_chars: int = 10000) -> ToolResult:
    target = Path(path).expanduser()
    if not target.is_file():
        return ToolResult.failure(f"Not a file: {target}")
    text = target.read_text(encoding="utf-8", errors="replace")[:max_chars]
    return ToolResult.success(text, path=str(target), length=len(text))


@tool(
    "delete_file",
    "Delete a file or empty directory.",
    {"type": "object", "properties": {"path": _PATH_ARG}, "required": ["path"]},
    destructive=True,
    category="files",
)
def delete_file(ctx: ToolContext, path: str) -> ToolResult:
    target = Path(path).expanduser()
    if not target.exists():
        return ToolResult.failure(f"Path does not exist: {target}")
    if target.is_dir():
        target.rmdir()
    else:
        target.unlink()
    return ToolResult.success(f"Deleted {target}")


@tool(
    "move_file",
    "Move or rename a file/folder.",
    {
        "type": "object",
        "properties": {"src": _PATH_ARG, "dst": _PATH_ARG},
        "required": ["src", "dst"],
    },
    destructive=True,
    category="files",
)
def move_file(ctx: ToolContext, src: str, dst: str) -> ToolResult:
    s, d = Path(src).expanduser(), Path(dst).expanduser()
    if not s.exists():
        return ToolResult.failure(f"Source missing: {s}")
    d.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(s), str(d))
    return ToolResult.success(f"Moved {s} -> {d}", path=str(d))


@tool(
    "copy_file",
    "Copy a file or directory tree.",
    {
        "type": "object",
        "properties": {"src": _PATH_ARG, "dst": _PATH_ARG},
        "required": ["src", "dst"],
    },
    category="files",
)
def copy_file(ctx: ToolContext, src: str, dst: str) -> ToolResult:
    s, d = Path(src).expanduser(), Path(dst).expanduser()
    if not s.exists():
        return ToolResult.failure(f"Source missing: {s}")
    if s.is_dir():
        shutil.copytree(s, d, dirs_exist_ok=True)
    else:
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(s, d)
    return ToolResult.success(f"Copied {s} -> {d}", path=str(d))


@tool(
    "search_folder",
    "Recursively search a folder for files matching a glob pattern.",
    {
        "type": "object",
        "properties": {
            "path": _PATH_ARG,
            "pattern": {"type": "string", "default": "*"},
            "limit": {"type": "integer", "default": 100},
        },
        "required": ["path"],
    },
    category="files",
)
def search_folder(ctx: ToolContext, path: str, pattern: str = "*", limit: int = 100) -> ToolResult:
    base = Path(path).expanduser()
    if not base.is_dir():
        return ToolResult.failure(f"Not a directory: {base}")
    matches = [str(p) for p in list(base.rglob(pattern))[:limit]]
    return ToolResult.success(f"Found {len(matches)} match(es).", matches=matches)


def get_tools() -> list[Tool]:
    return [
        create_file,
        create_folder,
        read_file,
        delete_file,
        move_file,
        copy_file,
        search_folder,
    ]
