"""Theme tokens and Qt stylesheet (dark glassmorphism, neon accents)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Theme:
    """Colour + geometry tokens for the dark, neon, glassmorphic look."""

    accent: str = "#22d3ee"          # neon cyan
    accent_soft: str = "#38bdf8"
    bg: str = "#0b1020"              # deep space blue
    bg_panel: str = "rgba(20, 28, 48, 0.72)"
    bg_elevated: str = "rgba(30, 41, 66, 0.85)"
    text: str = "#e5edff"
    text_muted: str = "#8ea0c4"
    danger: str = "#f87171"
    ok: str = "#4ade80"
    radius: int = 18

    def stylesheet(self) -> str:
        """Return the global Qt stylesheet for this theme."""
        return f"""
        QWidget {{
            background-color: transparent;
            color: {self.text};
            font-family: 'Segoe UI', 'SF Pro Display', 'Inter', sans-serif;
            font-size: 14px;
        }}
        #RootWindow {{
            background-color: {self.bg};
        }}
        #Panel, #Card {{
            background-color: {self.bg_panel};
            border: 1px solid rgba(120, 180, 255, 0.12);
            border-radius: {self.radius}px;
        }}
        QLabel#Title {{
            font-size: 20px;
            font-weight: 600;
            color: {self.text};
        }}
        QLabel#Caption {{
            font-size: 18px;
            color: {self.accent};
        }}
        QLabel#Subtle {{
            color: {self.text_muted};
        }}
        QTextEdit, QLineEdit, QListWidget, QPlainTextEdit {{
            background-color: {self.bg_elevated};
            border: 1px solid rgba(120, 180, 255, 0.15);
            border-radius: 12px;
            padding: 8px;
            selection-background-color: {self.accent};
        }}
        QPushButton {{
            background-color: {self.bg_elevated};
            border: 1px solid rgba(120, 180, 255, 0.18);
            border-radius: 12px;
            padding: 8px 14px;
        }}
        QPushButton:hover {{
            border: 1px solid {self.accent};
            color: {self.accent};
        }}
        QPushButton:pressed {{
            background-color: rgba(34, 211, 238, 0.15);
        }}
        QPushButton#ToolbarButton {{
            font-size: 20px;
            min-width: 52px;
            min-height: 52px;
            border-radius: 26px;
        }}
        QScrollBar:vertical {{
            background: transparent; width: 10px; margin: 2px;
        }}
        QScrollBar::handle:vertical {{
            background: rgba(120, 180, 255, 0.3); border-radius: 5px; min-height: 30px;
        }}
        """
