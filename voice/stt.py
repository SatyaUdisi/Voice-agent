"""Speech-to-text via OpenAI transcription.

Microphone capture (``sounddevice``) and the OpenAI SDK are both optional.
:meth:`SpeechToText.available` reports whether live transcription is possible so
callers can fall back to typed input.
"""

from __future__ import annotations

import io
import wave
from typing import Any

from logs import LogCategory, log_event

try:
    import numpy as np
    import sounddevice as sd
except Exception:  # pragma: no cover - optional / needs audio hw
    np = None  # type: ignore[assignment]
    sd = None  # type: ignore[assignment]


class SpeechToText:
    """Record from the microphone and transcribe with OpenAI."""

    def __init__(self, settings: Any) -> None:
        self._settings = settings
        self._client: Any = None
        if getattr(settings, "has_openai", False):
            try:
                from openai import OpenAI

                self._client = OpenAI(api_key=settings.openai_api_key)
            except Exception as exc:  # noqa: BLE001
                log_event(LogCategory.ERROR, "stt_init_failed", error=str(exc))

    @property
    def available(self) -> bool:
        """Whether both audio capture and transcription are usable."""
        return sd is not None and self._client is not None

    def record(self, seconds: float = 5.0) -> bytes | None:
        """Record audio and return 16-bit PCM WAV bytes (or ``None``)."""
        if sd is None or np is None:
            log_event(LogCategory.VOICE, "record_unavailable")
            return None
        rate = self._settings.sample_rate
        frames = sd.rec(int(seconds * rate), samplerate=rate, channels=1, dtype="int16")
        sd.wait()
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(rate)
            wf.writeframes(frames.tobytes())
        return buf.getvalue()

    def transcribe(self, wav_bytes: bytes) -> str:
        """Transcribe WAV bytes to text using the configured STT model."""
        if self._client is None:
            return ""
        try:
            buf = io.BytesIO(wav_bytes)
            buf.name = "audio.wav"
            result = self._client.audio.transcriptions.create(
                model=self._settings.stt_model, file=buf
            )
            text = getattr(result, "text", "") or ""
            log_event(LogCategory.VOICE, "transcribed", length=len(text))
            return text
        except Exception as exc:  # noqa: BLE001
            log_event(LogCategory.ERROR, "transcribe_failed", error=str(exc))
            return ""

    def listen(self, seconds: float = 5.0) -> str:
        """Convenience: record then transcribe."""
        audio = self.record(seconds)
        return self.transcribe(audio) if audio else ""
