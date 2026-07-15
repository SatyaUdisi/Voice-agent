"""Files panel: a lightweight browser of the local filesystem."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class FilesPanel(QWidget):
    """Navigate directories and preview text files."""

    def __init__(self, start: str | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Panel")
        self._cwd = Path(start or Path.home())

        root = QVBoxLayout(self)
        title = QLabel("Files")
        title.setObjectName("Title")
        root.addWidget(title)

        nav = QHBoxLayout()
        up = QPushButton("\u2191 Up")
        up.clicked.connect(self._go_up)
        self._path = QLineEdit(str(self._cwd))
        self._path.returnPressed.connect(self._go_to_typed)
        nav.addWidget(up)
        nav.addWidget(self._path, 1)
        root.addLayout(nav)

        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(self._on_open)
        root.addWidget(self._list, 1)

        self.refresh()

    def refresh(self) -> None:
        self._list.clear()
        self._path.setText(str(self._cwd))
        try:
            entries = sorted(
                self._cwd.iterdir(), key=lambda p: (p.is_file(), p.name.lower())
            )
        except OSError:
            return
        for entry in entries:
            glyph = "\U0001F4C1 " if entry.is_dir() else "\U0001F4C4 "
            item = QListWidgetItem(glyph + entry.name)
            item.setData(0x0100, str(entry))
            self._list.addItem(item)

    def _go_up(self) -> None:
        self._cwd = self._cwd.parent
        self.refresh()

    def _go_to_typed(self) -> None:
        candidate = Path(self._path.text()).expanduser()
        if candidate.is_dir():
            self._cwd = candidate
            self.refresh()

    def _on_open(self, item: QListWidgetItem) -> None:
        path = Path(item.data(0x0100))
        if path.is_dir():
            self._cwd = path
            self.refresh()
