# Installation Guide

## Requirements

- **Python 3.10+** (spec targets 3.13; the codebase is compatible with 3.10+).
- OS: Windows, macOS or Linux.
- For the GUI: a graphical display (X11/Wayland/Windows/macOS).
- For voice: a microphone + speakers and an OpenAI API key.

## 1. Clone and create a virtual environment

```bash
git clone <your-fork-url> voice-agent
cd voice-agent
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install --upgrade pip
```

## 2. Install dependencies

```bash
pip install -r requirements.txt
```

`requirements.txt` marks Windows-only packages (`pywin32`, `wmi`) with environment
markers so they install only on Windows.

## 3. Optional components

| Capability            | Extra step                                                   |
|-----------------------|--------------------------------------------------------------|
| Browser automation    | `playwright install chromium`                                |
| OCR (read screen text)| Install the tesseract binary (`apt install tesseract-ocr`, `brew install tesseract`, or the Windows installer) |
| Audio capture/playback| Ensure `sounddevice`/PortAudio is available; on Linux: `apt install libportaudio2` |
| Volume (Linux)        | `apt install alsa-utils` (`amixer`)                          |
| Brightness (Linux)    | `apt install brightnessctl`                                  |
| Volume (Windows)      | `pip install pycaw` (not bundled)                            |
| Brightness (Windows)  | `pip install screen-brightness-control` (not bundled)        |

> Every optional capability degrades gracefully: if it is missing, the related tool
> returns a clear error instead of failing the whole app.

## 4. Configure

```bash
cp .env.example .env
# edit .env and set VA_OPENAI_API_KEY plus any preferences
```

See [CONFIGURATION.md](CONFIGURATION.md) for every setting.

## 5. Run

```bash
python main.py            # GUI
python main.py --cli      # headless text REPL
python main.py --server   # FastAPI backend
```

## Headless Linux (CI / servers)

The GUI needs a display. For headless environments use `--cli`/`--server`, or run
under a virtual framebuffer:

```bash
sudo apt install xvfb
xvfb-run -a python main.py
```

## Troubleshooting

- **"Could not start GUI ... Falling back to CLI"** — no display or PySide6 missing.
  Use `--cli`/`--server`, or install a display / `PySide6`.
- **Offline mode banner** — no valid `VA_OPENAI_API_KEY`. Add one to `.env`.
- **No audio** — install PortAudio and check your input/output devices.
