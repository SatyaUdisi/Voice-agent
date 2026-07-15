"""Structured logging for the Voice Agent.

Exposes category-specific loggers (errors, tool calls, latency, LLM, automation,
voice) that write both human-readable text logs and machine-readable JSONL.
"""

from logs.logger import (
    LogCategory,
    configure_logging,
    get_logger,
    log_event,
)

__all__ = ["LogCategory", "configure_logging", "get_logger", "log_event"]
