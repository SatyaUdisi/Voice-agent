"""The main application window: orb, captions, transcript, toolbar and panels."""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from agent.events import AgentEvent, AgentEventType, AgentState
from assistant import Assistant, build_assistant
from gui.panels import ChatPanel, FilesPanel, LogsPanel, MemoryPanel, SettingsPanel
from gui.theme import Theme
from gui.widgets.orb import OrbWidget
from gui.widgets.toolbar import BottomToolbar
from gui.worker import AgentWorker, VoiceWorker

_STATE_LABEL = {
    AgentState.IDLE: "Idle",
    AgentState.LISTENING: "Listening...",
    AgentState.THINKING: "Thinking...",
    AgentState.SPEAKING: "Speaking...",
    AgentState.EXECUTING: "Executing task...",
}


class MainWindow(QWidget):
    """Root window hosting the orb-centric assistant UI."""

    def __init__(self, assistant: Assistant) -> None:
        super().__init__()
        self._assistant = assistant
        self._theme = Theme(accent=assistant.settings.accent_color)
        self._agent_worker: AgentWorker | None = None
        self._voice_worker: VoiceWorker | None = None
        self._dock: QDockWidget | None = None

        self.setObjectName("RootWindow")
        self.setWindowTitle("Voice Agent")
        self.resize(1080, 760)
        self.setStyleSheet(self._theme.stylesheet())

        assistant.set_confirm_fn(self._confirm)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 12)
        root.setSpacing(12)

        self._state_label = QLabel(_STATE_LABEL[AgentState.IDLE])
        self._state_label.setObjectName("Subtle")
        self._state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._state_label)

        self._orb = OrbWidget(animation_speed=assistant.settings.animation_speed)
        root.addWidget(self._orb, 1, alignment=Qt.AlignmentFlag.AlignCenter)

        self._caption = QLabel("Say \u201cHey Assistant\u201d or type below.")
        self._caption.setObjectName("Caption")
        self._caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._caption.setWordWrap(True)
        root.addWidget(self._caption)

        self._transcript = QTextEdit()
        self._transcript.setReadOnly(True)
        self._transcript.setObjectName("Card")
        self._transcript.setMaximumHeight(200)
        root.addWidget(self._transcript)

        input_row = QHBoxLayout()
        self._input = QLineEdit()
        self._input.setPlaceholderText("Type a command or question...")
        self._input.returnPressed.connect(self._on_send)
        send = QPushButton("Send")
        send.clicked.connect(self._on_send)
        input_row.addWidget(self._input, 1)
        input_row.addWidget(send)
        root.addLayout(input_row)

        self._toolbar = BottomToolbar()
        self._toolbar.mic_clicked.connect(self._on_mic)
        self._toolbar.panel_requested.connect(self._open_panel)
        root.addWidget(self._toolbar)

        if not assistant.llm.online:
            self._append("system", "Offline mode: set VA_OPENAI_API_KEY in .env for full capabilities.")

    # ------------------------------------------------------------------ #
    # Interaction
    # ------------------------------------------------------------------ #
    def _confirm(self, prompt: str) -> bool:
        button = QMessageBox.StandardButton
        reply = QMessageBox.question(self, "Confirm action", prompt, button.Yes | button.No)
        return reply == button.Yes

    def _append(self, role: str, text: str) -> None:
        color = {"user": self._theme.accent, "assistant": self._theme.text, "system": self._theme.text_muted}
        self._transcript.append(f'<span style="color:{color.get(role, self._theme.text)}"><b>{role}:</b> {text}</span>')

    def _on_send(self) -> None:
        text = self._input.text().strip()
        if not text:
            return
        self._input.clear()
        self._submit(text)

    def _submit(self, text: str) -> None:
        self._append("user", text)
        self._caption.setText(text)
        worker = AgentWorker(self._assistant, text, self)
        worker.agent_event.connect(self._on_agent_event)
        worker.finished_text.connect(self._on_agent_done)
        self._agent_worker = worker
        worker.start()

    def _on_mic(self) -> None:
        if not self._assistant.stt.available:
            self._append("system", "Microphone/STT unavailable (needs audio device + OpenAI key).")
            return
        self._set_state(AgentState.LISTENING)
        worker = VoiceWorker(self._assistant, seconds=5.0, parent=self)
        worker.transcript_ready.connect(self._on_transcript)
        self._voice_worker = worker
        worker.start()

    def _on_transcript(self, text: str) -> None:
        self._set_state(AgentState.IDLE)
        if not text:
            self._append("system", "Didn't catch that.")
            return
        command = text
        if self._assistant.settings.enable_wake_word and self._assistant.wake.detect(text):
            command = self._assistant.wake.strip_wake_word(text)
        self._submit(command)

    # ------------------------------------------------------------------ #
    # Agent events
    # ------------------------------------------------------------------ #
    def _set_state(self, state: AgentState) -> None:
        self._orb.set_state(state)
        self._state_label.setText(_STATE_LABEL.get(state, ""))

    def _on_agent_event(self, event: AgentEvent) -> None:
        if event.type == AgentEventType.STATE and event.state is not None:
            self._set_state(event.state)
        elif event.type == AgentEventType.TOOL_START:
            self._append("system", f"\u2699 {event.data['name']}({event.data.get('arguments', {})})")
        elif event.type == AgentEventType.TOOL_RESULT:
            status = "ok" if event.data.get("ok") else "failed"
            self._append("system", f"\u2192 [{status}] {event.data.get('output', '')[:200]}")
        elif event.type == AgentEventType.MESSAGE:
            self._caption.setText(event.data.get("text", ""))
        elif event.type == AgentEventType.ERROR:
            self._append("system", f"Error: {event.data.get('error')}")

    def _on_agent_done(self, reply: str) -> None:
        self._set_state(AgentState.IDLE)
        if reply:
            self._append("assistant", reply)
            self._caption.setText(reply)

    # ------------------------------------------------------------------ #
    # Panels
    # ------------------------------------------------------------------ #
    def _open_panel(self, key: str) -> None:
        factories = {
            "chat": lambda: ChatPanel(self._assistant),
            "settings": lambda: SettingsPanel(self._assistant),
            "files": lambda: FilesPanel(),
            "memory": lambda: MemoryPanel(self._assistant),
            "logs": lambda: LogsPanel(self._assistant),
        }
        factory = factories.get(key)
        if factory is None:
            return
        if self._dock is not None:
            self._dock.close()
        dock = QDockWidget(key.capitalize(), self)
        dock.setWidget(factory())
        dock.setMinimumWidth(420)
        dock.setFloating(True)
        dock.resize(460, 620)
        dock.show()
        self._dock = dock

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        self._assistant.shutdown()
        super().closeEvent(event)


def run_gui() -> int:
    """Launch the desktop GUI. Returns the Qt exit code."""
    assistant = build_assistant()
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow(assistant)
    window.show()
    return app.exec()
