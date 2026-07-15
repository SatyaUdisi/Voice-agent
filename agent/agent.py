"""The agent reasoning loop.

Implements Think -> Plan -> Choose -> Execute -> Verify -> Respond using OpenAI
tool calling. Emits :class:`AgentEvent` objects through a callback so the GUI can
update the orb state, show plans, tool activity and stream the final answer.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from agent.events import AgentEvent, AgentEventType, AgentState
from agent.llm import LLMClient
from agent.prompts import build_system_prompt
from database.models import TaskRecord
from logs import LogCategory, log_event
from memory.manager import MemoryManager
from tools.base import ToolRegistry

EventSink = Callable[[AgentEvent], None]


class Agent:
    """Coordinates the LLM, tools and memory to fulfil a user request."""

    def __init__(
        self,
        llm: LLMClient,
        registry: ToolRegistry,
        memory: MemoryManager,
        *,
        max_steps: int = 12,
    ) -> None:
        self._llm = llm
        self._registry = registry
        self._memory = memory
        self._max_steps = max_steps

    def _emit(self, sink: EventSink | None, event: AgentEvent) -> None:
        if sink is not None:
            sink(event)

    def _set_state(self, sink: EventSink | None, state: AgentState) -> None:
        self._emit(sink, AgentEvent(type=AgentEventType.STATE, state=state))

    def run(self, user_input: str, on_event: EventSink | None = None) -> str:
        """Process one user turn and return the final assistant reply.

        The full multi-step loop runs synchronously; call from a worker thread
        in the GUI. Progress is streamed via ``on_event``.
        """
        self._memory.add_user_message(user_input)
        task = self._memory.record_task(TaskRecord(goal=user_input, status="running"))
        task_id = task.id or 0

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": build_system_prompt(self._memory.build_context())},
        ]
        # Include recent conversation history for continuity.
        for msg in self._memory.history(limit=12):
            if msg.role in ("user", "assistant"):
                messages.append({"role": msg.role, "content": msg.content})

        tools = self._registry.openai_schemas()
        final_text = ""

        try:
            self._set_state(on_event, AgentState.THINKING)
            for _step in range(self._max_steps):
                response = self._llm.chat(messages, tools=tools)

                if not response.tool_calls:
                    final_text = response.content
                    if final_text:
                        self._emit(
                            on_event,
                            AgentEvent(type=AgentEventType.MESSAGE, data={"text": final_text}),
                        )
                    break

                # Record the assistant's tool-call turn.
                messages.append(
                    {
                        "role": "assistant",
                        "content": response.content or None,
                        "tool_calls": [
                            {
                                "id": c.id,
                                "type": "function",
                                "function": {
                                    "name": c.name,
                                    "arguments": json.dumps(c.arguments),
                                },
                            }
                            for c in response.tool_calls
                        ],
                    }
                )

                self._set_state(on_event, AgentState.EXECUTING)
                for call in response.tool_calls:
                    self._emit(
                        on_event,
                        AgentEvent(
                            type=AgentEventType.TOOL_START,
                            data={"name": call.name, "arguments": call.arguments},
                        ),
                    )
                    result = self._registry.call(call.name, call.arguments)
                    self._emit(
                        on_event,
                        AgentEvent(
                            type=AgentEventType.TOOL_RESULT,
                            data={"name": call.name, "ok": result.ok, "output": result.output},
                        ),
                    )
                    # Feed the (verified) tool result back to the model.
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.id,
                            "content": json.dumps({"ok": result.ok, "output": result.output}),
                        }
                    )
                self._set_state(on_event, AgentState.THINKING)
            else:
                final_text = final_text or "I reached the maximum number of steps for this task."

            self._memory.add_assistant_message(final_text)
            self._memory.update_task(task_id, "success", final_text[:500])
        except Exception as exc:  # noqa: BLE001
            log_event(LogCategory.ERROR, "agent_run_failed", error=str(exc))
            self._memory.update_task(task_id, "failed", str(exc))
            self._emit(on_event, AgentEvent(type=AgentEventType.ERROR, data={"error": str(exc)}))
            final_text = f"Sorry, something went wrong: {exc}"
        finally:
            self._set_state(on_event, AgentState.IDLE)
            self._emit(on_event, AgentEvent(type=AgentEventType.DONE, data={"text": final_text}))

        return final_text
