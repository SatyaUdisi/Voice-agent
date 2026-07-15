"""Shared pytest fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure the project root is importable when running `pytest` from anywhere.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.settings import Settings  # noqa: E402
from database.db import Database  # noqa: E402
from memory.manager import MemoryManager  # noqa: E402
from tools.base import ToolContext  # noqa: E402
from tools.registry import build_default_registry  # noqa: E402


@pytest.fixture()
def settings(tmp_path: Path) -> Settings:
    return Settings(
        openai_api_key="",
        db_path=str(tmp_path / "test.db"),
        log_dir=str(tmp_path / "logs"),
    )


@pytest.fixture()
def db(settings: Settings) -> Database:
    database = Database(settings.db_file)
    yield database
    database.close()


@pytest.fixture()
def memory(db: Database) -> MemoryManager:
    return MemoryManager(db)


@pytest.fixture()
def registry(settings: Settings, memory: MemoryManager):
    ctx = ToolContext(settings=settings, memory=memory, confirm=lambda _p: True)
    return build_default_registry(ctx)
