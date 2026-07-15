"""Thin wrapper over the OpenAI Chat Completions API with tool calling.

Normalises the provider response into a small :class:`LLMResponse` so the agent
loop does not depend on SDK internals. When no API key is configured the client
runs in **offline mode**, returning a helpful canned reply so the whole app
(GUI, tools, memory) remains runnable without credentials.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from logs import LogCategory, log_event


@dataclass(slots=True)
class ToolCall:
    """A normalised tool/function call requested by the model."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(slots=True)
class LLMResponse:
    """Normalised chat completion result."""

    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLMClient:
    """OpenAI-backed chat client with graceful offline fallback."""

    def __init__(self, settings: Any) -> None:
        self._settings = settings
        self._client: Any = None
        if getattr(settings, "has_openai", False):
            try:
                from openai import OpenAI

                self._client = OpenAI(api_key=settings.openai_api_key)
            except Exception as exc:  # noqa: BLE001
                log_event(LogCategory.ERROR, "openai_init_failed", error=str(exc))
                self._client = None

    @property
    def online(self) -> bool:
        return self._client is not None

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        """Run a (non-streaming) chat completion, optionally with tools."""
        if not self.online:
            return self._offline_response(messages)

        start = time.perf_counter()
        try:
            resp = self._client.chat.completions.create(
                model=self._settings.llm_model,
                messages=messages,
                tools=tools or None,
                tool_choice="auto" if tools else None,
            )
        except Exception as exc:  # noqa: BLE001
            log_event(LogCategory.ERROR, "llm_chat_failed", error=str(exc))
            return LLMResponse(content=f"(LLM error: {exc})")

        elapsed = (time.perf_counter() - start) * 1000
        log_event(LogCategory.LATENCY, "llm_chat", elapsed_ms=round(elapsed, 2))

        msg = resp.choices[0].message
        calls: list[ToolCall] = []
        for tc in msg.tool_calls or []:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            calls.append(ToolCall(id=tc.id, name=tc.function.name, arguments=args))
        log_event(LogCategory.LLM, "llm_response", tool_calls=[c.name for c in calls])
        return LLMResponse(content=msg.content or "", tool_calls=calls)

    def _offline_response(self, messages: list[dict[str, Any]]) -> LLMResponse:
        """Deterministic response used when no API key is configured."""
        last_user = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "user"),
            "",
        )
        text = (
            "I'm running in offline mode (no OpenAI API key configured), so I "
            "can't reason with the LLM or call tools autonomously yet. "
            f'You said: "{last_user}". Add VA_OPENAI_API_KEY to your .env to '
            "enable full agent capabilities."
        )
        return LLMResponse(content=text)
