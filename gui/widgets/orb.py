"""The central animated glowing orb.

Renders a smooth, pulsing radial-gradient sphere whose colour and motion depend
on the current :class:`AgentState`. Driven by a ~60 FPS ``QTimer``.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QRadialGradient
from PySide6.QtWidgets import QWidget

from agent.events import AgentState

# Base colour per state (RGB).
_STATE_COLORS: dict[AgentState, tuple[int, int, int]] = {
    AgentState.IDLE: (34, 211, 238),       # cyan
    AgentState.LISTENING: (74, 222, 128),  # green
    AgentState.THINKING: (168, 85, 247),   # purple
    AgentState.SPEAKING: (56, 189, 248),   # sky blue
    AgentState.EXECUTING: (251, 191, 36),  # amber
}


class OrbWidget(QWidget):
    """A stateful, animated orb rendered with radial gradients."""

    def __init__(self, animation_speed: float = 1.0, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._phase = 0.0
        self._speed = max(0.1, animation_speed)
        self._state = AgentState.IDLE
        self.setMinimumSize(260, 260)

        # ~60 FPS animation loop.
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

    def set_state(self, state: AgentState) -> None:
        """Switch the orb's visual state."""
        self._state = state
        self.update()

    def set_animation_speed(self, speed: float) -> None:
        self._speed = max(0.1, speed)

    def _tick(self) -> None:
        # Faster motion when actively working.
        rate = 0.06 if self._state in (AgentState.THINKING, AgentState.EXECUTING) else 0.03
        self._phase = (self._phase + rate * self._speed) % (2 * math.pi)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        base = min(w, h) * 0.32
        pulse = 1.0 + 0.08 * math.sin(self._phase)
        radius = base * pulse

        r, g, b = _STATE_COLORS.get(self._state, _STATE_COLORS[AgentState.IDLE])

        # Outer glow.
        glow = QRadialGradient(QPointF(cx, cy), radius * 2.1)
        glow.setColorAt(0.0, QColor(r, g, b, 90))
        glow.setColorAt(0.5, QColor(r, g, b, 40))
        glow.setColorAt(1.0, QColor(r, g, b, 0))
        painter.setBrush(glow)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), radius * 2.1, radius * 2.1)

        # Core sphere.
        core = QRadialGradient(QPointF(cx - radius * 0.3, cy - radius * 0.3), radius * 1.6)
        core.setColorAt(0.0, QColor(255, 255, 255, 230))
        core.setColorAt(0.25, QColor(min(r + 60, 255), min(g + 60, 255), min(b + 60, 255), 235))
        core.setColorAt(1.0, QColor(r, g, b, 235))
        painter.setBrush(core)
        painter.drawEllipse(QPointF(cx, cy), radius, radius)

        # Rotating highlight ring for "thinking"/"executing".
        if self._state in (AgentState.THINKING, AgentState.EXECUTING):
            painter.setBrush(Qt.BrushStyle.NoBrush)
            pen = painter.pen()
            pen.setColor(QColor(255, 255, 255, 120))
            pen.setWidth(3)
            painter.setPen(pen)
            span = 90 * 16
            start = int(math.degrees(self._phase) * 16)
            painter.drawArc(
                int(cx - radius * 1.4),
                int(cy - radius * 1.4),
                int(radius * 2.8),
                int(radius * 2.8),
                start,
                span,
            )
        painter.end()
