"""SQLite database access layer with typed repository methods."""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from database.models import (
    Conversation,
    MemoryItem,
    Message,
    Preference,
    TaskRecord,
)

_SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    """Thread-safe wrapper around a single SQLite connection.

    Uses a re-entrant lock so it can be shared across the GUI thread, the
    asyncio backend and worker threads without corrupting the connection.
    """

    def __init__(self, db_file: Path | str) -> None:
        self._path = Path(db_file)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(
            str(self._path), check_same_thread=False, isolation_level=None
        )
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.executescript(_SCHEMA_PATH.read_text(encoding="utf-8"))

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # ------------------------------------------------------------------ #
    # Conversations & messages
    # ------------------------------------------------------------------ #
    def create_conversation(self, title: str = "New conversation") -> Conversation:
        ts = _now()
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO conversations(title, created_at, updated_at) VALUES (?,?,?)",
                (title, ts, ts),
            )
            return Conversation(id=cur.lastrowid, title=title, created_at=ts, updated_at=ts)

    def add_message(self, conversation_id: int, role: str, content: str) -> Message:
        ts = _now()
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO messages(conversation_id, role, content, created_at) VALUES (?,?,?,?)",
                (conversation_id, role, content, ts),
            )
            self._conn.execute(
                "UPDATE conversations SET updated_at=? WHERE id=?", (ts, conversation_id)
            )
            return Message(
                id=cur.lastrowid,
                conversation_id=conversation_id,
                role=role,
                content=content,
                created_at=ts,
            )

    def get_messages(self, conversation_id: int, limit: int = 200) -> list[Message]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM messages WHERE conversation_id=? ORDER BY id ASC LIMIT ?",
                (conversation_id, limit),
            ).fetchall()
        return [Message(**dict(r)) for r in rows]

    def list_conversations(self, limit: int = 100) -> list[Conversation]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM conversations ORDER BY updated_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [Conversation(**dict(r)) for r in rows]

    def delete_conversation(self, conversation_id: int) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM conversations WHERE id=?", (conversation_id,))

    def search_messages(self, query: str, limit: int = 50) -> list[Message]:
        """Full-text search over message content (for 'search old chats')."""
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT m.* FROM messages_fts f
                JOIN messages m ON m.id = f.rowid
                WHERE messages_fts MATCH ?
                ORDER BY m.id DESC LIMIT ?
                """,
                (query, limit),
            ).fetchall()
        return [Message(**dict(r)) for r in rows]

    # ------------------------------------------------------------------ #
    # Preferences
    # ------------------------------------------------------------------ #
    def set_preference(self, key: str, value: str) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO preferences(key, value, updated_at) VALUES (?,?,?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
                """,
                (key, value, _now()),
            )

    def get_preference(self, key: str, default: str | None = None) -> str | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT value FROM preferences WHERE key=?", (key,)
            ).fetchone()
        return row["value"] if row else default

    def all_preferences(self) -> list[Preference]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM preferences").fetchall()
        return [Preference(**dict(r)) for r in rows]

    # ------------------------------------------------------------------ #
    # Long-term memory
    # ------------------------------------------------------------------ #
    def add_memory(self, item: MemoryItem) -> MemoryItem:
        with self._lock:
            cur = self._conn.execute(
                """
                INSERT INTO memory(kind, content, importance, usage_count, created_at, last_used_at)
                VALUES (?,?,?,?,?,?)
                """,
                (
                    item.kind,
                    item.content,
                    item.importance,
                    item.usage_count,
                    item.created_at,
                    item.last_used_at,
                ),
            )
            item.id = cur.lastrowid
        return item

    def top_memories(self, kind: str | None = None, limit: int = 20) -> list[MemoryItem]:
        with self._lock:
            if kind:
                rows = self._conn.execute(
                    "SELECT * FROM memory WHERE kind=? ORDER BY importance DESC, usage_count DESC LIMIT ?",
                    (kind, limit),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM memory ORDER BY importance DESC, usage_count DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [MemoryItem(**dict(r)) for r in rows]

    def touch_memory(self, memory_id: int) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE memory SET usage_count = usage_count + 1, last_used_at=? WHERE id=?",
                (_now(), memory_id),
            )

    # ------------------------------------------------------------------ #
    # Tasks
    # ------------------------------------------------------------------ #
    def record_task(self, task: TaskRecord) -> TaskRecord:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO tasks(goal, plan, status, result, created_at) VALUES (?,?,?,?,?)",
                (task.goal, task.plan, task.status, task.result, task.created_at),
            )
            task.id = cur.lastrowid
        return task

    def update_task(self, task_id: int, status: str, result: str = "") -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE tasks SET status=?, result=? WHERE id=?", (status, result, task_id)
            )

    def recent_tasks(self, limit: int = 20) -> list[TaskRecord]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM tasks ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [TaskRecord(**dict(r)) for r in rows]
