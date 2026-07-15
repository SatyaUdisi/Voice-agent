"""Logs panel: tails the structured JSONL logs by category."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from assistant import Assistant
from logs import LogCategory


class LogsPanel(QWidget):
    """Displays recent structured log events for a chosen category."""

    def __init__(self, assistant: Assistant, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._log_dir: Path = assistant.settings.log_path
        self.setObjectName("Panel")

        root = QVBoxLayout(self)
        title = QLabel("Logs")
        title.setObjectName("Title")
        root.addWidget(title)

        row = QHBoxLayout()
        self._category = QComboBox()
        self._category.addItems([c.value for c in LogCategory])
        self._category.currentTextChanged.connect(self.refresh)
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.refresh)
        row.addWidget(self._category, 1)
        row.addWidget(refresh)
        root.addLayout(row)

        self._view = QPlainTextEdit()
        self._view.setReadOnly(True)
        root.addWidget(self._view, 1)

        self.refresh()

    def refresh(self) -> None:
        category = self._category.currentText()
        path = self._log_dir / f"{category}.jsonl"
        if not path.exists():
            self._view.setPlainText("(no log entries yet)")
            return
        lines = path.read_text(encoding="utf-8").splitlines()[-200:]
        rendered = []
        for line in lines:
            try:
                rec = json.loads(line)
                extra = {k: v for k, v in rec.items() if k not in ("ts", "category", "level", "message")}
                rendered.append(f"{rec['ts'][11:19]} {rec['message']} {extra or ''}")
            except json.JSONDecodeError:
                rendered.append(line)
        self._view.setPlainText("\n".join(rendered))
