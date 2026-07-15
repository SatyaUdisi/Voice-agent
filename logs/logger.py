"""Structured, category-aware logging.

The Voice Agent emits many kinds of operational events. Rather than dumping
everything into one file, events are tagged with a :class:`LogCategory` and
written to:

* a rotating human-readable ``voice_agent.log`` (all categories), and
* per-category JSONL files (``tool_calls.jsonl``, ``llm.jsonl`` ...) that are
  easy to parse for the GUI "Logs" panel and for latency analysis.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from enum import Enum
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()
_CONFIGURED = False
_JSONL_HANDLES: dict[str, Any] = {}
_LOG_DIR: Path | None = None


class LogCategory(str, Enum):
    """Categories used to route and filter log events."""

    ERROR = "error"
    TOOL_CALL = "tool_call"
    LATENCY = "latency"
    LLM = "llm"
    AUTOMATION = "automation"
    VOICE = "voice"
    AGENT = "agent"
    SYSTEM = "system"


def configure_logging(log_dir: Path | str, level: str = "INFO") -> None:
    """Initialise logging. Idempotent — safe to call multiple times."""
    global _CONFIGURED, _LOG_DIR
    with _LOCK:
        if _CONFIGURED:
            return
        _LOG_DIR = Path(log_dir)
        _LOG_DIR.mkdir(parents=True, exist_ok=True)

        root = logging.getLogger("voice_agent")
        root.setLevel(getattr(logging, level.upper(), logging.INFO))
        root.propagate = False

        fmt = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        file_handler = RotatingFileHandler(
            _LOG_DIR / "voice_agent.log",
            maxBytes=5_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(fmt)

        console = logging.StreamHandler()
        console.setFormatter(fmt)

        root.handlers.clear()
        root.addHandler(file_handler)
        root.addHandler(console)
        _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the ``voice_agent`` namespace."""
    return logging.getLogger(f"voice_agent.{name}")


def _jsonl_handle(category: LogCategory):
    """Lazily open (and cache) the JSONL file handle for a category."""
    if _LOG_DIR is None:
        return None
    if category.value not in _JSONL_HANDLES:
        path = _LOG_DIR / f"{category.value}.jsonl"
        _JSONL_HANDLES[category.value] = path.open("a", encoding="utf-8")
    return _JSONL_HANDLES[category.value]


def log_event(
    category: LogCategory,
    message: str,
    *,
    level: int = logging.INFO,
    **fields: Any,
) -> None:
    """Log a structured event to both the text log and category JSONL file.

    Args:
        category: The event category (routes to a JSONL file).
        message: Human-readable message.
        level: ``logging`` level constant.
        **fields: Arbitrary JSON-serialisable structured fields.
    """
    logger = get_logger(category.value)
    logger.log(level, "%s %s", message, fields if fields else "")

    handle = _jsonl_handle(category)
    if handle is None:
        return
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "category": category.value,
        "level": logging.getLevelName(level),
        "message": message,
        **fields,
    }
    with _LOCK:
        handle.write(json.dumps(record, default=str) + "\n")
        handle.flush()
