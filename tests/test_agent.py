"""Tests for the agent loop and its verification behaviour."""

from __future__ import annotations

from agent.agent import Agent
from agent.events import AgentEventType, AgentState
from agent.llm import LLMResponse, ToolCall


class FakeLLM:
    """Scripted LLM: returns queued responses in order."""

    def __init__(self, responses: list[LLMResponse]) -> None:
        self._responses = responses
        self.online = True
        self.calls: list[list[dict]] = []

    def chat(self, messages, tools=None) -> LLMResponse:
        self.calls.append(messages)
        return self._responses.pop(0)


def test_agent_plain_reply(registry, memory) -> None:
    llm = FakeLLM([LLMResponse(content="Hello!")])
    agent = Agent(llm, registry, memory, max_steps=3)
    reply = agent.run("hi")
    assert reply == "Hello!"
    assert memory.history()[-1].content == "Hello!"


def test_agent_executes_tool_then_responds(registry, memory, tmp_path) -> None:
    target = tmp_path / "note.txt"
    responses = [
        LLMResponse(
            tool_calls=[ToolCall(id="1", name="create_file", arguments={"path": str(target), "content": "x"})]
        ),
        LLMResponse(content="Created the file."),
    ]
    llm = FakeLLM(responses)
    events: list = []
    agent = Agent(llm, registry, memory, max_steps=5)
    reply = agent.run("make a file", on_event=events.append)

    assert target.exists()
    assert reply == "Created the file."
    types = [e.type for e in events]
    assert AgentEventType.TOOL_START in types
    assert AgentEventType.TOOL_RESULT in types
    assert any(e.state == AgentState.EXECUTING for e in events if e.state)


def test_agent_reports_tool_failure_truthfully(registry, memory) -> None:
    responses = [
        LLMResponse(tool_calls=[ToolCall(id="1", name="read_file", arguments={"path": "/no/such/file"})]),
        LLMResponse(content="I could not read that file."),
    ]
    llm = FakeLLM(responses)
    events: list = []
    agent = Agent(llm, registry, memory)
    agent.run("read it", on_event=events.append)
    tool_results = [e for e in events if e.type == AgentEventType.TOOL_RESULT]
    assert tool_results and tool_results[0].data["ok"] is False
