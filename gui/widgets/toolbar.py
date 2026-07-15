"""Bottom toolbar with the primary action buttons."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget


class BottomToolbar(QWidget):
    """Row of round icon buttons: mic, chat, settings, files, memory, logs."""

    mic_clicked = Signal()
    panel_requested = Signal(str)

    _BUTTONS = [
        ("mic", "\U0001F3A4", "Microphone"),        # 🎤
        ("chat", "\U0001F4AC", "Chat history"),      # 💬
        ("settings", "\u2699", "Settings"),          # ⚙
        ("files", "\U0001F4C2", "Files"),            # 📂
        ("memory", "\U0001F9E0", "Memory"),          # 🧠
        ("logs", "\U0001F4CA", "Logs"),              # 📊
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(14)
        layout.addStretch(1)

        for key, glyph, tip in self._BUTTONS:
            btn = QPushButton(glyph)
            btn.setObjectName("ToolbarButton")
            btn.setToolTip(tip)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if key == "mic":
                btn.clicked.connect(self.mic_clicked.emit)
            else:
                btn.clicked.connect(lambda _=False, k=key: self.panel_requested.emit(k))
            layout.addWidget(btn)

        layout.addStretch(1)
