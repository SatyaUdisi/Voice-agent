"""Tests for wake-word detection (no audio hardware required)."""

from __future__ import annotations

from voice.wake_word import WakeWordDetector


def test_detects_wake_words() -> None:
    detector = WakeWordDetector(["hey assistant", "jarvis"])
    assert detector.detect("Jarvis, what time is it?")
    assert detector.detect("hey assistant open chrome")
    assert not detector.detect("just a normal sentence")


def test_strips_wake_word() -> None:
    detector = WakeWordDetector(["jarvis"])
    assert detector.strip_wake_word("Jarvis, open the browser") == "open the browser"


def test_empty_wake_words() -> None:
    detector = WakeWordDetector([])
    assert not detector.detect("anything")
