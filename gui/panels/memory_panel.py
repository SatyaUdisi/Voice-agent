"""Memory panel: view facts, frequent apps/folders and add new memories."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from assistant import Assistant
from database.models import MemoryItem


class MemoryPanel(QWidget):
    """Displays long-term memory and lets the user add facts."""

    def __init__(self, assistant: Assistant, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._assistant = assistant
        self.setObjectName("Panel")

        root = QVBoxLayout(self)
        title = QLabel("Memory")
        title.setObjectName("Title")
        root.addWidget(title)

        self._view = QTextEdit()
        self._view.setReadOnly(True)
        root.addWidget(self._view, 1)

        add_row = QHBoxLayout()
        self._input = QLineEdit()
        self._input.setPlaceholderText("Remember this fact...")
        self._input.returnPressed.connect(self._on_add)
        add_btn = QPushButton("Remember")
        add_btn.clicked.connect(self._on_add)
        add_row.addWidget(self._input, 1)
        add_row.addWidget(add_btn)
        root.addLayout(add_row)

        self.refresh()

    def refresh(self) -> None:
        db = self._assistant.db
        lines: list[str] = ["Facts:"]
        lines += [f"  - {m.content}" for m in db.top_memories(kind="fact", limit=30)]
        lines.append("\nFrequent apps:")
        lines += [f"  - {a}" for a in self._assistant.memory.frequent("app", top=10)]
        lines.append("\nFrequent folders:")
        lines += [f"  - {f}" for f in self._assistant.memory.frequent("folder", top=10)]
        lines.append("\nRecent tasks:")
        lines += [f"  - [{t.status}] {t.goal}" for t in db.recent_tasks(limit=10)]
        self._view.setPlainText("\n".join(lines))

    def _on_add(self) -> None:
        text = self._input.text().strip()
        if not text:
            return
        self._assistant.db.add_memory(MemoryItem(kind="fact", content=text, importance=0.7))
        self._input.clear()
        self.refresh()
