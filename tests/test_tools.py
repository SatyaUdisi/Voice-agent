"""Tests for the tool system and representative tools."""

from __future__ import annotations

from pathlib import Path


def test_registry_has_expected_categories(registry) -> None:
    categories = {t.category for t in registry.all()}
    assert {"files", "system", "desktop", "browser", "productivity", "coding", "vision"} <= categories


def test_openai_schemas_are_wellformed(registry) -> None:
    for schema in registry.openai_schemas():
        assert schema["type"] == "function"
        assert "name" in schema["function"]
        assert schema["function"]["parameters"]["type"] == "object"


def test_file_lifecycle(registry, tmp_path: Path) -> None:
    target = tmp_path / "sub" / "hello.txt"
    created = registry.call("create_file", {"path": str(target), "content": "hi"})
    assert created.ok and target.read_text() == "hi"

    read = registry.call("read_file", {"path": str(target)})
    assert read.ok and read.output == "hi"

    moved = registry.call("move_file", {"src": str(target), "dst": str(tmp_path / "moved.txt")})
    assert moved.ok and (tmp_path / "moved.txt").exists()

    deleted = registry.call("delete_file", {"path": str(tmp_path / "moved.txt")})
    assert deleted.ok


def test_calculator(registry) -> None:
    result = registry.call("calculator", {"expression": "3*(4+5)/2"})
    assert result.ok and result.data["value"] == 13.5


def test_calculator_rejects_code(registry) -> None:
    result = registry.call("calculator", {"expression": "__import__('os').system('echo hi')"})
    assert not result.ok


def test_run_python(registry) -> None:
    result = registry.call("run_python", {"code": "print(2 + 2)"})
    assert result.ok and "4" in result.output


def test_unknown_tool(registry) -> None:
    assert not registry.call("nope", {}).ok


def test_destructive_confirmation_declined(settings, memory) -> None:
    from tools.base import ToolContext
    from tools.registry import build_default_registry

    ctx = ToolContext(settings=settings, memory=memory, confirm=lambda _p: False)
    reg = build_default_registry(ctx)
    result = reg.call("delete_file", {"path": "/tmp/whatever"})
    assert not result.ok and "declined" in result.output.lower()
