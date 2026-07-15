"""FastAPI backend exposing the agent over HTTP + WebSocket.

Useful for headless operation, remote frontends, or integration tests. The GUI
can run standalone; this server is an optional, decoupled interface to the same
:class:`Assistant` core.
"""

from __future__ import annotations

import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from agent.events import AgentEvent
from assistant import Assistant, build_assistant


class ChatRequest(BaseModel):
    """Request body for the synchronous chat endpoint."""

    message: str


class ChatResponse(BaseModel):
    """Response body for the synchronous chat endpoint."""

    reply: str


def create_app(assistant: Assistant | None = None) -> FastAPI:
    """Build the FastAPI application wired to an :class:`Assistant`."""
    app = FastAPI(title="Voice Agent API", version="1.0.0")
    core = assistant or build_assistant()
    app.state.assistant = core

    @app.get("/health")
    def health() -> dict[str, object]:
        return {
            "status": "ok",
            "online": core.llm.online,
            "platform": core.platform.summary(),
            "tools": len(core.registry.all()),
        }

    @app.get("/tools")
    def list_tools() -> dict[str, list[dict[str, str]]]:
        return {
            "tools": [
                {"name": t.name, "category": t.category, "description": t.description}
                for t in core.registry.all()
            ]
        }

    @app.post("/chat", response_model=ChatResponse)
    def chat(req: ChatRequest) -> ChatResponse:
        return ChatResponse(reply=core.handle_text(req.message))

    @app.websocket("/ws")
    async def ws(websocket: WebSocket) -> None:
        """Stream agent events for a message over a WebSocket."""
        await websocket.accept()
        try:
            while True:
                raw = await websocket.receive_text()
                message = json.loads(raw).get("message", "")
                events: list[AgentEvent] = []
                reply = core.handle_text(message, on_event=events.append)
                for evt in events:
                    await websocket.send_json(
                        {"type": evt.type.value, "state": evt.state.value if evt.state else None, "data": evt.data}
                    )
                await websocket.send_json({"type": "reply", "data": {"text": reply}})
        except WebSocketDisconnect:
            return

    return app


app = None  # lazily created by run_server to avoid import-time side effects


def run_server() -> None:
    """Run the API server with uvicorn using configured host/port."""
    import uvicorn

    core = build_assistant()
    application = create_app(core)
    uvicorn.run(application, host=core.settings.api_host, port=core.settings.api_port)
