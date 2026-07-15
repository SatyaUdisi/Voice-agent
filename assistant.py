"""Composition root / dependency-injection container.

Builds and wires every subsystem (settings, logging, database, memory, tools,
LLM, agent, voice) into a single :class:`Assistant` facade that both the GUI and
the FastAPI backend consume. This keeps construction in one place and the rest of
the codebase free of global state.
"""

from __future__ import annotations

from collections.abc import Callable

from agent.agent import Agent
from agent.events import AgentEvent
from agent.llm import LLMClient
from automation.permissions import PermissionManager
from automation.platform import PlatformInfo, current_platform
from config.settings import Settings, get_settings
from database.db import Database
from logs import LogCategory, configure_logging, log_event
from memory.manager import MemoryManager
from tools.base import ToolContext
from tools.registry import build_default_registry
from voice.stt import SpeechToText
from voice.tts import TextToSpeech
from voice.wake_word import WakeWordDetector


class Assistant:
    """Facade over the fully-wired agent stack."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings: Settings = settings or get_settings()
        configure_logging(self.settings.log_path, self.settings.log_level)

        self.platform: PlatformInfo = current_platform()
        self.db = Database(self.settings.db_file)
        self.memory = MemoryManager(self.db)

        self.permissions = PermissionManager(
            automation_enabled=self.settings.enable_automation,
            confirm_destructive=self.settings.confirm_destructive,
        )

        context = ToolContext(
            settings=self.settings,
            memory=self.memory,
            confirm=self.permissions.confirm,
        )
        self.registry = build_default_registry(context)

        self.llm = LLMClient(self.settings)
        self.agent = Agent(
            self.llm,
            self.registry,
            self.memory,
            max_steps=self.settings.max_agent_steps,
        )

        self.stt = SpeechToText(self.settings)
        self.tts = TextToSpeech(self.settings)
        self.wake = WakeWordDetector(self.settings.wake_words)

        log_event(
            LogCategory.SYSTEM,
            "assistant_initialised",
            platform=self.platform.summary(),
            online=self.llm.online,
            tools=len(self.registry.all()),
        )

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def set_confirm_fn(self, fn: Callable[[str], bool] | None) -> None:
        """Provide the interactive confirmation callback (from the GUI)."""
        self.permissions.set_confirm_fn(fn)

    def handle_text(self, text: str, on_event: Callable[[AgentEvent], None] | None = None) -> str:
        """Run a text turn through the agent and return the reply."""
        return self.agent.run(text, on_event=on_event)

    def handle_voice(self, seconds: float = 5.0, on_event=None) -> tuple[str, str]:
        """Record + transcribe, run the agent, and speak the reply.

        Returns a ``(transcript, reply)`` tuple.
        """
        transcript = self.stt.listen(seconds) if self.stt.available else ""
        if not transcript:
            return "", ""
        reply = self.handle_text(transcript, on_event=on_event)
        if self.tts.available:
            self.tts.speak(reply)
        return transcript, reply

    def shutdown(self) -> None:
        self.db.close()
        log_event(LogCategory.SYSTEM, "assistant_shutdown")


def build_assistant() -> Assistant:
    """Factory used by entrypoints."""
    return Assistant()
