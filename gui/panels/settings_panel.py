"""Settings panel: API keys, voice, theme, wake word, automation, etc.

Edits are persisted to the ``preferences`` table so they survive restarts.
(API keys shown here are stored in preferences for convenience; the canonical
source remains the ``.env`` file / environment.)
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from assistant import Assistant


class SettingsPanel(QWidget):
    """Editable application settings backed by the preferences store."""

    def __init__(self, assistant: Assistant, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._assistant = assistant
        self.setObjectName("Panel")
        settings = assistant.settings

        root = QVBoxLayout(self)
        title = QLabel("Settings")
        title.setObjectName("Title")
        root.addWidget(title)

        form = QFormLayout()

        self._api_key = QLineEdit(self._pref("openai_api_key", settings.openai_api_key))
        self._api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key.setPlaceholderText("sk-...")
        form.addRow("OpenAI API key", self._api_key)

        self._llm_model = QLineEdit(self._pref("llm_model", settings.llm_model))
        form.addRow("LLM model", self._llm_model)

        self._voice = QLineEdit(self._pref("tts_voice", settings.tts_voice))
        form.addRow("TTS voice", self._voice)

        self._wake = QLineEdit(self._pref("wake_words", ",".join(settings.wake_words)))
        form.addRow("Wake words", self._wake)

        self._theme = QLineEdit(self._pref("theme", settings.theme))
        form.addRow("Theme", self._theme)

        self._anim = QDoubleSpinBox()
        self._anim.setRange(0.1, 3.0)
        self._anim.setSingleStep(0.1)
        self._anim.setValue(float(self._pref("animation_speed", str(settings.animation_speed))))
        form.addRow("Animation speed", self._anim)

        self._automation = QCheckBox("Enable automation")
        self._automation.setChecked(self._pref("enable_automation", str(settings.enable_automation)) == "True")
        form.addRow("Automation", self._automation)

        self._confirm = QCheckBox("Confirm destructive actions")
        self._confirm.setChecked(self._pref("confirm_destructive", str(settings.confirm_destructive)) == "True")
        form.addRow("Safety", self._confirm)

        root.addLayout(form)

        save = QPushButton("Save settings")
        save.clicked.connect(self._on_save)
        root.addWidget(save)

        self._status = QLabel("")
        self._status.setObjectName("Subtle")
        root.addWidget(self._status)
        root.addStretch(1)

    def _pref(self, key: str, default: str) -> str:
        return self._assistant.memory.get_preference(key, default) or default

    def _on_save(self) -> None:
        mem = self._assistant.memory
        mem.set_preference("openai_api_key", self._api_key.text().strip())
        mem.set_preference("llm_model", self._llm_model.text().strip())
        mem.set_preference("tts_voice", self._voice.text().strip())
        mem.set_preference("wake_words", self._wake.text().strip())
        mem.set_preference("theme", self._theme.text().strip())
        mem.set_preference("animation_speed", str(self._anim.value()))
        mem.set_preference("enable_automation", str(self._automation.isChecked()))
        mem.set_preference("confirm_destructive", str(self._confirm.isChecked()))
        self._status.setText("Saved. Some changes apply after restart.")
