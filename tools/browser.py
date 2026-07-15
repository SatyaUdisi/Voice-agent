"""Browser-automation tools backed by Playwright (sync API).

A single browser + page is lazily created and reused across calls. Playwright
is optional; if it (or its browsers) are not installed, tools return a helpful
message instructing the user to run ``playwright install``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.base import Tool, ToolContext, ToolResult, tool

try:
    from playwright.sync_api import sync_playwright
except Exception:  # pragma: no cover - optional dependency
    sync_playwright = None  # type: ignore[assignment]


class _BrowserSession:
    """Lazily-initialised, reusable Playwright browser session."""

    def __init__(self) -> None:
        self._pw: Any = None
        self._browser: Any = None
        self._page: Any = None

    def page(self, headless: bool = True) -> Any:
        if sync_playwright is None:
            raise RuntimeError(
                "Playwright not installed. Run: pip install playwright && playwright install"
            )
        if self._page is None:
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(headless=headless)
            self._page = self._browser.new_page()
        return self._page

    def close(self) -> None:
        for obj, method in ((self._browser, "close"), (self._pw, "stop")):
            try:
                if obj is not None:
                    getattr(obj, method)()
            except Exception:  # noqa: BLE001, S110 - best-effort teardown
                pass
        self._pw = self._browser = self._page = None


_SESSION = _BrowserSession()


@tool(
    "browser_open",
    "Open the browser and navigate to a URL.",
    {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "headless": {"type": "boolean", "default": True},
        },
        "required": ["url"],
    },
    category="browser",
)
def browser_open(ctx: ToolContext, url: str, headless: bool = True) -> ToolResult:
    try:
        page = _SESSION.page(headless=headless)
        page.goto(url, wait_until="domcontentloaded")
    except Exception as exc:  # noqa: BLE001
        return ToolResult.failure(str(exc))
    return ToolResult.success(f"Opened {url}", title=page.title(), url=page.url)


@tool(
    "browser_search",
    "Search Google for a query and return the current page title/URL.",
    {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    category="browser",
)
def browser_search(ctx: ToolContext, query: str) -> ToolResult:
    from urllib.parse import quote_plus

    return browser_open.handler(ctx, url=f"https://www.google.com/search?q={quote_plus(query)}")


@tool(
    "browser_click",
    "Click the first element matching a CSS/text selector.",
    {"type": "object", "properties": {"selector": {"type": "string"}}, "required": ["selector"]},
    category="browser",
)
def browser_click(ctx: ToolContext, selector: str) -> ToolResult:
    try:
        page = _SESSION.page()
        page.click(selector, timeout=8000)
    except Exception as exc:  # noqa: BLE001
        return ToolResult.failure(str(exc))
    return ToolResult.success(f"Clicked {selector}", url=page.url)


@tool(
    "browser_fill",
    "Fill an input field identified by a selector with a value.",
    {
        "type": "object",
        "properties": {"selector": {"type": "string"}, "value": {"type": "string"}},
        "required": ["selector", "value"],
    },
    category="browser",
)
def browser_fill(ctx: ToolContext, selector: str, value: str) -> ToolResult:
    try:
        page = _SESSION.page()
        page.fill(selector, value, timeout=8000)
    except Exception as exc:  # noqa: BLE001
        return ToolResult.failure(str(exc))
    return ToolResult.success(f"Filled {selector}")


@tool(
    "browser_read",
    "Return the visible text of the current page (truncated).",
    {"type": "object", "properties": {"max_chars": {"type": "integer", "default": 5000}}},
    category="browser",
)
def browser_read(ctx: ToolContext, max_chars: int = 5000) -> ToolResult:
    try:
        page = _SESSION.page()
        text = page.inner_text("body")[:max_chars]
    except Exception as exc:  # noqa: BLE001
        return ToolResult.failure(str(exc))
    return ToolResult.success(text, length=len(text))


@tool(
    "browser_summarize",
    "Read the current page and summarise it with the LLM (needs OpenAI key).",
    {"type": "object", "properties": {}},
    category="browser",
)
def browser_summarize(ctx: ToolContext) -> ToolResult:
    read = browser_read.handler(ctx, max_chars=8000)
    if not read.ok:
        return read
    settings = ctx.settings
    if settings is None or not getattr(settings, "has_openai", False):
        # Fall back to returning the raw text if we cannot summarise.
        return ToolResult.success(read.output[:1000], note="No OpenAI key; returned raw excerpt.")
    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        resp = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": "Summarise the web page content concisely."},
                {"role": "user", "content": read.output},
            ],
        )
        return ToolResult.success(resp.choices[0].message.content or "")
    except Exception as exc:  # noqa: BLE001
        return ToolResult.failure(f"Summarisation failed: {exc}")


@tool(
    "browser_download",
    "Download a file from a direct URL to a local path.",
    {
        "type": "object",
        "properties": {"url": {"type": "string"}, "path": {"type": "string"}},
        "required": ["url", "path"],
    },
    category="browser",
)
def browser_download(ctx: ToolContext, url: str, path: str) -> ToolResult:
    import urllib.request

    dest = Path(path).expanduser()
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        urllib.request.urlretrieve(url, dest)  # noqa: S310 - user-directed download
    except Exception as exc:  # noqa: BLE001
        return ToolResult.failure(f"Download failed: {exc}")
    if not dest.exists():
        return ToolResult.failure("Download reported success but file is missing.")
    return ToolResult.success(f"Downloaded to {dest}", path=str(dest), size=dest.stat().st_size)


def get_tools() -> list[Tool]:
    return [
        browser_open,
        browser_search,
        browser_click,
        browser_fill,
        browser_read,
        browser_summarize,
        browser_download,
    ]
