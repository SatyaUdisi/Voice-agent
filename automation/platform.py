"""Platform detection and capability reporting."""

from __future__ import annotations

import platform
import shutil
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlatformInfo:
    """Describes the host OS and which automation capabilities are available."""

    system: str
    is_windows: bool
    is_mac: bool
    is_linux: bool
    has_display: bool

    def summary(self) -> str:
        caps = []
        if self.has_display:
            caps.append("display")
        return f"{self.system} ({', '.join(caps) or 'headless'})"


def current_platform() -> PlatformInfo:
    """Return information about the current platform."""
    system = platform.system()
    has_display = _detect_display(system)
    return PlatformInfo(
        system=system,
        is_windows=system == "Windows",
        is_mac=system == "Darwin",
        is_linux=system == "Linux",
        has_display=has_display,
    )


def _detect_display(system: str) -> bool:
    if system == "Windows" or system == "Darwin":
        return True
    # Linux: a display is present if DISPLAY/WAYLAND is set and X tooling exists.
    import os

    if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
        return True
    return bool(shutil.which("Xorg") or shutil.which("Xvfb"))
