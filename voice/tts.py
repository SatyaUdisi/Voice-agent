"""Text-to-speech via OpenAI, with optional local playback.

Synthesises speech to MP3 bytes and (when audio output is available) plays it.
Degrades gracefully to a no-op when no key / audio backend is present.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from logs import LogCategory, log_event


class TextToSpeech:
    """Synthesise and play assistant speech."""

    def __init__(self, settings: Any) -> None:
        self._settings = settings
        self._client: Any = None
        if getattr(settings, "has_openai", False):
            try:
                from openai import OpenAI

                self._client = OpenAI(api_key=settings.openai_api_key)
            except Exception as exc:  # noqa: BLE001
                log_event(LogCategory.ERROR, "tts_init_failed", error=str(exc))

    @property
    def available(self) -> bool:
        return self._client is not None

    def synthesize(self, text: str, out_path: str | Path | None = None) -> bytes | None:
        """Return MP3 audio bytes for ``text`` (also writing to disk if asked)."""
        if self._client is None or not text.strip():
            return None
        try:
            resp = self._client.audio.speech.create(
                model=self._settings.tts_model,
                voice=self._settings.tts_voice,
                input=text,
            )
            audio = resp.read() if hasattr(resp, "read") else bytes(resp)
        except Exception as exc:  # noqa: BLE001
            log_event(LogCategory.ERROR, "tts_failed", error=str(exc))
            return None
        if out_path is not None:
            Path(out_path).write_bytes(audio)
        log_event(LogCategory.VOICE, "synthesized", chars=len(text))
        return audio

    def speak(self, text: str) -> bool:
        """Synthesise and attempt to play speech. Returns True on playback."""
        audio = self.synthesize(text)
        if audio is None:
            return False
        return self._play(audio)

    def _play(self, mp3_bytes: bytes) -> bool:
        """Best-effort local playback of MP3 bytes."""
        try:
            import tempfile

            from playsound import playsound  # type: ignore

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as fh:
                fh.write(mp3_bytes)
                path = fh.name
            playsound(path)
            return True
        except Exception:  # noqa: BLE001 - playback is best-effort
            log_event(LogCategory.VOICE, "playback_unavailable")
            return False
