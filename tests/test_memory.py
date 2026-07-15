"""Tests for the database and memory manager."""

from __future__ import annotations

from database.models import MemoryItem


def test_conversation_and_messages(memory) -> None:
    memory.add_user_message("hello")
    memory.add_assistant_message("hi there")
    history = memory.history()
    assert [m.role for m in history] == ["user", "assistant"]


def test_full_text_search(memory) -> None:
    memory.add_user_message("remind me about the quarterly report")
    memory.add_assistant_message("sure")
    results = memory.search("quarterly")
    assert any("quarterly" in m.content for m in results)


def test_preferences_roundtrip(memory) -> None:
    memory.set_preference("theme", "dark")
    assert memory.get_preference("theme") == "dark"


def test_long_term_memory_and_context(db, memory) -> None:
    db.add_memory(MemoryItem(kind="fact", content="User prefers metric units", importance=0.9))
    memory.note_app_usage("code")
    memory.note_app_usage("code")
    context = memory.build_context()
    assert "metric units" in context
    assert "code" in context


def test_frequent_apps(memory) -> None:
    for _ in range(3):
        memory.note_app_usage("firefox")
    memory.note_app_usage("slack")
    freq = memory.frequent("app")
    assert freq[0] == "firefox"
