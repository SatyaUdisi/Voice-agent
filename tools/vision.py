"""Vision tools: screenshots, OCR and screen understanding.

Screenshots use ``pyautogui``/``Pillow``. OCR uses ``pytesseract`` (requires the
``tesseract`` binary). Higher-level "understand the screen" delegates to the
configured OpenAI vision model when a key is present.
"""

from __future__ import annotations

import base64
from datetime import datetime
from pathlib import Path

from tools.base import Tool, ToolContext, ToolResult, tool

try:
    import pyautogui
except Exception:  # pragma: no cover
    pyautogui = None  # type: ignore[assignment]

try:
    import pytesseract
    from PIL import Image
except Exception:  # pragma: no cover
    pytesseract = None  # type: ignore[assignment]
    Image = None  # type: ignore[assignment]


def _screens_dir(ctx: ToolContext) -> Path:
    root = Path.cwd() / "assets" / "screenshots"
    root.mkdir(parents=True, exist_ok=True)
    return root


@tool(
    "take_screenshot",
    "Capture the current screen to a PNG file and return its path.",
    {"type": "object", "properties": {"path": {"type": "string"}}},
    category="vision",
)
def take_screenshot(ctx: ToolContext, path: str | None = None) -> ToolResult:
    if pyautogui is None:
        return ToolResult.failure("Screenshot unavailable (no display / pyautogui missing).")
    out = Path(path).expanduser() if path else _screens_dir(ctx) / f"screen_{datetime.now():%Y%m%d_%H%M%S}.png"
    try:
        img = pyautogui.screenshot()
        img.save(out)
    except Exception as exc:  # noqa: BLE001
        return ToolResult.failure(f"Screenshot failed: {exc}")
    return ToolResult.success(f"Saved screenshot to {out}", path=str(out))


@tool(
    "read_screen_text",
    "Run OCR on a screenshot (or the live screen) and return recognised text.",
    {"type": "object", "properties": {"image_path": {"type": "string"}}},
    category="vision",
)
def read_screen_text(ctx: ToolContext, image_path: str | None = None) -> ToolResult:
    if pytesseract is None or Image is None:
        return ToolResult.failure("OCR unavailable (install pytesseract + tesseract binary).")
    try:
        if image_path:
            img = Image.open(image_path)
        elif pyautogui is not None:
            img = pyautogui.screenshot()
        else:
            return ToolResult.failure("No image provided and screen capture unavailable.")
        text = pytesseract.image_to_string(img)
    except Exception as exc:  # noqa: BLE001
        return ToolResult.failure(f"OCR failed: {exc}")
    return ToolResult.success(text.strip() or "(no text detected)", length=len(text))


@tool(
    "analyze_screen",
    "Describe/understand the screen using a vision model (needs OpenAI key).",
    {
        "type": "object",
        "properties": {
            "question": {"type": "string", "default": "Describe what is on the screen."},
            "image_path": {"type": "string"},
        },
    },
    category="vision",
)
def analyze_screen(
    ctx: ToolContext,
    question: str = "Describe what is on the screen.",
    image_path: str | None = None,
) -> ToolResult:
    settings = ctx.settings
    if settings is None or not getattr(settings, "has_openai", False):
        return ToolResult.failure("Vision analysis needs a configured OpenAI API key.")

    # Ensure we have an image on disk to send.
    if image_path is None:
        shot = take_screenshot.handler(ctx)
        if not shot.ok:
            return shot
        image_path = shot.data["path"]

    try:
        from openai import OpenAI

        data = Path(image_path).read_bytes()
        b64 = base64.b64encode(data).decode()
        client = OpenAI(api_key=settings.openai_api_key)
        resp = client.chat.completions.create(
            model=settings.vision_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                    ],
                }
            ],
        )
        answer = resp.choices[0].message.content or ""
    except Exception as exc:  # noqa: BLE001
        return ToolResult.failure(f"Vision request failed: {exc}")
    return ToolResult.success(answer, image_path=image_path)


def get_tools() -> list[Tool]:
    return [take_screenshot, read_screen_text, analyze_screen]
