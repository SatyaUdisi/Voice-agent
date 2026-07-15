"""High-level memory manager.

Sits on top of :class:`~database.db.Database` and provides the agent with:

* the active conversation and its history,
* user preferences,
* long-term memory facts, and
* a compact "memory context" string that is injected into the system prompt.
"""

from __future__ import annotations

from collections import Counter

from database.db import Database
from database.models import Conversation, MemoryItem, Message, TaskRecord
from logs import LogCategory, log_event


class MemoryManager:
    """Coordinates short-term (conversation) and long-term memory."""

    def __init__(self, db: Database) -> None:
        self._db = db
        self._conversation: Conversation | None = None

    # ------------------------------------------------------------------ #
    # Conversation lifecycle
    # ------------------------------------------------------------------ #
    @property
    def conversation(self) -> Conversation:
        """Return the active conversation, creating one on first access."""
        if self._conversation is None:
            self._conversation = self._db.create_conversation()
        return self._conversation

    @property
    def conversation_id(self) -> int:
        """The active conversation id (always populated)."""
        cid = self.conversation.id
        assert cid is not None  # noqa: S101 - created rows always have an id
        return cid

    def start_new_conversation(self, title: str = "New conversation") -> Conversation:
        self._conversation = self._db.create_conversation(title)
        return self._conversation

    def load_conversation(self, conversation_id: int) -> list[Message]:
        convs = {c.id: c for c in self._db.list_conversations(limit=1000)}
        if conversation_id in convs:
            self._conversation = convs[conversation_id]
        return self._db.get_messages(conversation_id)

    def add_user_message(self, content: str) -> Message:
        return self._db.add_message(self.conversation_id, "user", content)

    def add_assistant_message(self, content: str) -> Message:
        return self._db.add_message(self.conversation_id, "assistant", content)

    def history(self, limit: int = 20) -> list[Message]:
        return self._db.get_messages(self.conversation_id, limit=limit)

    def search(self, query: str, limit: int = 50) -> list[Message]:
        return self._db.search_messages(query, limit=limit)

    # ------------------------------------------------------------------ #
    # Preferences
    # ------------------------------------------------------------------ #
    def set_preference(self, key: str, value: str) -> None:
        self._db.set_preference(key, value)
        log_event(LogCategory.SYSTEM, "preference_set", key=key)

    def get_preference(self, key: str, default: str | None = None) -> str | None:
        return self._db.get_preference(key, default)

    # ------------------------------------------------------------------ #
    # Long-term memory
    # ------------------------------------------------------------------ #
    def remember(self, content: str, kind: str = "fact", importance: float = 0.5) -> MemoryItem:
        item = self._db.add_memory(
            MemoryItem(kind=kind, content=content, importance=importance)
        )
        log_event(LogCategory.SYSTEM, "memory_added", kind=kind, importance=importance)
        return item

    def note_app_usage(self, app: str) -> None:
        """Track a frequently used application in memory."""
        self.remember(app, kind="app", importance=0.6)

    def note_folder_usage(self, folder: str) -> None:
        self.remember(folder, kind="folder", importance=0.6)

    def record_task(self, task: TaskRecord) -> TaskRecord:
        return self._db.record_task(task)

    def update_task(self, task_id: int, status: str, result: str = "") -> None:
        self._db.update_task(task_id, status, result)

    # ------------------------------------------------------------------ #
    # Context building
    # ------------------------------------------------------------------ #
    def frequent(self, kind: str, top: int = 5) -> list[str]:
        """Return the most frequently used items of a given kind."""
        items = self._db.top_memories(kind=kind, limit=100)
        counter: Counter[str] = Counter()
        for item in items:
            counter[item.content] += item.usage_count + 1
        return [name for name, _ in counter.most_common(top)]

    def build_context(self) -> str:
        """Build a compact memory summary to inject into the system prompt."""
        facts = self._db.top_memories(kind="fact", limit=8)
        apps = self.frequent("app")
        folders = self.frequent("folder")
        tasks = self._db.recent_tasks(limit=5)

        lines: list[str] = []
        if facts:
            lines.append("Known facts about the user:")
            lines.extend(f"  - {f.content}" for f in facts)
        if apps:
            lines.append(f"Frequently used apps: {', '.join(apps)}")
        if folders:
            lines.append(f"Frequently used folders: {', '.join(folders)}")
        if tasks:
            lines.append("Recent tasks:")
            lines.extend(f"  - [{t.status}] {t.goal}" for t in tasks)
        return "\n".join(lines)
