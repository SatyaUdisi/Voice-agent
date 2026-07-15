"""Agent state + event types used to drive the GUI and voice subsystems."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentState(str, Enum):
    """High-level agent states, mapped 1:1 to the GUI orb animations."""

    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    EXECUTING = "executing"


class AgentEventType(str, Enum):
    """Discrete events emitted during a turn."""

    STATE = "state"           # agent changed state
    PLAN = "plan"             # produced a plan
    TOKEN = "token"           # streamed response token  # noqa: S105
    TOOL_START = "tool_start"
    TOOL_RESULT = "tool_result"
    MESSAGE = "message"       # a complete assistant message
    ERROR = "error"
    DONE = "done"


@dataclass(slots=True)
class AgentEvent:
    """A single event emitted by the agent loop."""

    type: AgentEventType
    data: dict[str, Any] = field(default_factory=dict)
    state: AgentState | None = None
