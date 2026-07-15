"""Background workers that keep the agent + voice off the GUI thread."""

from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal

from agent.events import AgentEvent
from assistant import Assistant


class AgentWorker(QThread):
    """Runs a single agent turn in a background thread.

    Emits :attr:`agent_event` for each :class:`AgentEvent` and :attr:`finished_text`
    with the final reply. The GUI connects to these to update the orb, captions
    and transcript without blocking the event loop.
    """

    agent_event = Signal(object)    # AgentEvent
    finished_text = Signal(str)     # final reply

    def __init__(self, assistant: Assistant, text: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._assistant = assistant
        self._text = text

    def run(self) -> None:  # noqa: D401 - QThread entrypoint
        def sink(evt: AgentEvent) -> None:
            self.agent_event.emit(evt)

        reply = self._assistant.handle_text(self._text, on_event=sink)
        self.finished_text.emit(reply)


class VoiceWorker(QThread):
    """Records + transcribes speech in the background and emits the transcript."""

    transcript_ready = Signal(str)

    def __init__(self, assistant: Assistant, seconds: float = 5.0, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._assistant = assistant
        self._seconds = seconds

    def run(self) -> None:  # noqa: D401
        stt = self._assistant.stt
        text = stt.listen(self._seconds) if stt.available else ""
        self.transcript_ready.emit(text)
