"""Dataclass models mirroring the SQLite schema."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class Conversation:
    """A chat session grouping a series of messages."""

    id: int | None = None
    title: str = "New conversation"
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)


@dataclass(slots=True)
class Message:
    """A single message within a conversation."""

    id: int | None = None
    conversation_id: int = 0
    role: str = "user"  # user | assistant | tool | system
    content: str = ""
    created_at: str = field(default_factory=_now)


@dataclass(slots=True)
class Preference:
    """A key/value user preference (e.g. favourite apps, voice)."""

    key: str = ""
    value: str = ""
    updated_at: str = field(default_factory=_now)


@dataclass(slots=True)
class MemoryItem:
    """A long-term memory fact with an importance weight and usage count."""

    id: int | None = None
    kind: str = "fact"  # fact | app | folder | task
    content: str = ""
    importance: float = 0.5
    usage_count: int = 0
    created_at: str = field(default_factory=_now)
    last_used_at: str = field(default_factory=_now)


@dataclass(slots=True)
class TaskRecord:
    """A record of a task the agent attempted, with its verification outcome."""

    id: int | None = None
    goal: str = ""
    plan: str = ""
    status: str = "pending"  # pending | running | success | failed
    result: str = ""
    created_at: str = field(default_factory=_now)
