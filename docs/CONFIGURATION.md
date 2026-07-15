# Configuration Guide

All configuration is via environment variables (prefixed `VA_`) and/or a `.env` file
at the project root. Settings are parsed and validated by
[`config/settings.py`](../config/settings.py) using Pydantic.

Copy `.env.example` to `.env` and edit.

## API setup

1. Create an API key at <https://platform.openai.com/api-keys>.
2. Put it in `.env` as `VA_OPENAI_API_KEY=sk-...`.
3. Set the model names your account can access.

## Settings reference

| Variable                | Default                      | Description |
|-------------------------|------------------------------|-------------|
| `VA_OPENAI_API_KEY`     | *(empty)*                    | OpenAI API key. Empty → offline mode. |
| `VA_LLM_MODEL`          | `gpt-5`                      | Reasoning / chat model. |
| `VA_REALTIME_MODEL`     | `gpt-4o-realtime-preview`    | Realtime voice model. |
| `VA_STT_MODEL`          | `whisper-1`                  | Speech-to-text model. |
| `VA_TTS_MODEL`          | `gpt-4o-mini-tts`            | Text-to-speech model. |
| `VA_TTS_VOICE`          | `alloy`                      | TTS voice. |
| `VA_VISION_MODEL`       | `gpt-5`                      | Vision model for screen understanding. |
| `VA_WAKE_WORDS`         | `hey assistant,jarvis`       | Comma-separated wake phrases. |
| `VA_ENABLE_WAKE_WORD`   | `true`                       | Require a wake word for voice input. |
| `VA_SILENCE_TIMEOUT_MS` | `1200`                       | Silence before end-of-utterance. |
| `VA_SAMPLE_RATE`        | `16000`                      | Microphone sample rate (Hz). |
| `VA_THEME`              | `dark`                       | GUI theme. |
| `VA_ANIMATION_SPEED`    | `1.0`                        | Orb animation speed multiplier. |
| `VA_ACCENT_COLOR`       | `#22d3ee`                    | Neon accent colour. |
| `VA_MAX_AGENT_STEPS`    | `12`                         | Max tool-calling iterations per turn. |
| `VA_ENABLE_AUTOMATION`  | `true`                       | Master switch for automation tools. |
| `VA_CONFIRM_DESTRUCTIVE`| `true`                       | Confirm before destructive tools (delete/close/move). |
| `VA_DB_PATH`            | `database/voice_agent.db`    | SQLite database path. |
| `VA_LOG_DIR`            | `logs`                       | Log output directory. |
| `VA_LOG_LEVEL`          | `INFO`                       | Logging level. |
| `VA_API_HOST`           | `127.0.0.1`                  | FastAPI bind host. |
| `VA_API_PORT`           | `8765`                       | FastAPI port. |

## Settings in the GUI

The **Settings** panel (⚙ in the toolbar) lets you edit the API key, model, voice,
wake words, theme, animation speed and automation/safety toggles at runtime. Values
are stored in the `preferences` table; the canonical source remains `.env`.

## Safety & permissions

- `VA_ENABLE_AUTOMATION=false` disables all automation tools.
- `VA_CONFIRM_DESTRUCTIVE=true` routes destructive tools (delete/close/move) through a
  confirmation callback — in the GUI this is a dialog; in the CLI a `[y/N]` prompt.
