"""Lightweight wake-word detection.

This is a pragmatic, dependency-free detector that matches configured wake
phrases (e.g. "hey assistant", "jarvis") against transcribed text. For always-on
audio wake detection you can swap in openWakeWord / Porcupine behind the same
interface.
"""

from __future__ import annotations

import re
from collections.abc import Iterable


class WakeWordDetector:
    """Detects wake phrases within a transcript and returns the command tail."""

    def __init__(self, wake_words: Iterable[str]) -> None:
        self._wake_words = [w.strip().lower() for w in wake_words if w.strip()]
        self._patterns = [
            re.compile(rf"\b{re.escape(w)}\b", re.IGNORECASE) for w in self._wake_words
        ]

    @property
    def wake_words(self) -> list[str]:
        return list(self._wake_words)

    def detect(self, text: str) -> bool:
        """Return True if any wake phrase is present in ``text``."""
        return any(p.search(text) for p in self._patterns)

    def strip_wake_word(self, text: str) -> str:
        """Remove the wake phrase and return the remaining command."""
        out = text
        for pattern in self._patterns:
            out = pattern.sub("", out, count=1)
        return out.strip(" ,.-\t")
