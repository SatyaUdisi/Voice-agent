"""Chat-history panel: browse, search, export and delete conversations."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from assistant import Assistant


class ChatPanel(QWidget):
    """Lists conversations, supports full-text search, export and delete."""

    def __init__(self, assistant: Assistant, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._assistant = assistant
        self.setObjectName("Panel")

        root = QVBoxLayout(self)
        title = QLabel("Chat History")
        title.setObjectName("Title")
        root.addWidget(title)

        search_row = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search old chats...")
        self._search.returnPressed.connect(self._on_search)
        search_row.addWidget(self._search)
        root.addLayout(search_row)

        self._list = QListWidget()
        self._list.itemClicked.connect(self._on_select)
        root.addWidget(self._list, 1)

        self._view = QTextEdit()
        self._view.setReadOnly(True)
        root.addWidget(self._view, 2)

        btn_row = QHBoxLayout()
        export_btn = QPushButton("Export")
        export_btn.clicked.connect(self._on_export)
        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(self._on_delete)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        btn_row.addWidget(refresh_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(export_btn)
        btn_row.addWidget(delete_btn)
        root.addLayout(btn_row)

        self.refresh()

    def refresh(self) -> None:
        self._list.clear()
        for conv in self._assistant.db.list_conversations():
            item = QListWidgetItem(f"#{conv.id}  {conv.title}  ({conv.updated_at[:19]})")
            item.setData(0x0100, conv.id)  # Qt.UserRole
            self._list.addItem(item)

    def _current_id(self) -> int | None:
        item = self._list.currentItem()
        return item.data(0x0100) if item else None

    def _render_messages(self, conv_id: int) -> str:
        msgs = self._assistant.db.get_messages(conv_id)
        return "\n\n".join(f"[{m.role}] {m.content}" for m in msgs)

    def _on_select(self, item: QListWidgetItem) -> None:
        conv_id = item.data(0x0100)
        self._view.setPlainText(self._render_messages(conv_id))

    def _on_search(self) -> None:
        query = self._search.text().strip()
        if not query:
            self.refresh()
            return
        results = self._assistant.memory.search(query)
        self._view.setPlainText(
            "\n\n".join(f"[conv {m.conversation_id}] {m.content}" for m in results)
            or "(no matches)"
        )

    def _on_export(self) -> None:
        conv_id = self._current_id()
        if conv_id is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export conversation", f"chat_{conv_id}.txt")
        if path:
            Path(path).write_text(self._render_messages(conv_id), encoding="utf-8")

    def _on_delete(self) -> None:
        conv_id = self._current_id()
        if conv_id is None:
            return
        self._assistant.db.delete_conversation(conv_id)
        self._view.clear()
        self.refresh()
