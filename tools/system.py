"""System-information and control tools (CPU/RAM/battery/volume/etc.).

Read-only metrics use ``psutil`` when available. Hardware-control actions
(volume, brightness) are platform-specific and degrade gracefully with a clear
message when the underlying capability is unavailable.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
from datetime import datetime

from tools.base import Tool, ToolContext, ToolResult, tool

try:
    import psutil
except Exception:  # pragma: no cover - optional dependency
    psutil = None  # type: ignore[assignment]

IS_WINDOWS = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"


def _need_psutil() -> ToolResult | None:
    if psutil is None:
        return ToolResult.failure("psutil is not installed; system metrics unavailable.")
    return None


@tool("get_datetime", "Return the current local date and time.", category="system")
def get_datetime(ctx: ToolContext) -> ToolResult:
    now = datetime.now()
    return ToolResult.success(now.strftime("%A, %Y-%m-%d %H:%M:%S"), iso=now.isoformat())


@tool("get_cpu", "Return current CPU utilisation percentage and core count.", category="system")
def get_cpu(ctx: ToolContext) -> ToolResult:
    if (err := _need_psutil()) is not None:
        return err
    pct = psutil.cpu_percent(interval=0.3)
    return ToolResult.success(f"CPU {pct}% across {psutil.cpu_count()} cores", percent=pct)


@tool("get_ram", "Return current RAM usage.", category="system")
def get_ram(ctx: ToolContext) -> ToolResult:
    if (err := _need_psutil()) is not None:
        return err
    vm = psutil.virtual_memory()
    gb = 1024**3
    return ToolResult.success(
        f"RAM {vm.percent}% used ({vm.used/gb:.1f}/{vm.total/gb:.1f} GB)",
        percent=vm.percent,
    )


@tool("get_battery", "Return battery percentage and charging status.", category="system")
def get_battery(ctx: ToolContext) -> ToolResult:
    if (err := _need_psutil()) is not None:
        return err
    batt = getattr(psutil, "sensors_battery", lambda: None)()
    if batt is None:
        return ToolResult.failure("No battery detected on this machine.")
    state = "charging" if batt.power_plugged else "on battery"
    return ToolResult.success(f"Battery {batt.percent}% ({state})", percent=batt.percent)


@tool(
    "list_processes",
    "List top processes by memory usage.",
    {"type": "object", "properties": {"limit": {"type": "integer", "default": 10}}},
    category="system",
)
def list_processes(ctx: ToolContext, limit: int = 10) -> ToolResult:
    if (err := _need_psutil()) is not None:
        return err
    procs = []
    for p in psutil.process_iter(["pid", "name", "memory_percent"]):
        try:
            procs.append(p.info)
        except Exception:  # noqa: BLE001, S112 - skip processes we can't read
            continue
    procs.sort(key=lambda x: x.get("memory_percent") or 0, reverse=True)
    top = procs[:limit]
    listing = ", ".join(f"{p['name']}({p['pid']})" for p in top)
    return ToolResult.success(listing or "no processes", processes=top)


@tool("get_wifi_status", "Report whether the machine has an active network connection.", category="system")
def get_wifi_status(ctx: ToolContext) -> ToolResult:
    if (err := _need_psutil()) is not None:
        return err
    stats = psutil.net_if_stats()
    up = [name for name, s in stats.items() if s.isup and name != "lo"]
    if up:
        return ToolResult.success(f"Online via: {', '.join(up)}", interfaces=up)
    return ToolResult.failure("No active network interfaces detected.")


@tool(
    "set_volume",
    "Set the system output volume (0-100). Platform dependent.",
    {"type": "object", "properties": {"level": {"type": "integer"}}, "required": ["level"]},
    category="system",
)
def set_volume(ctx: ToolContext, level: int) -> ToolResult:
    level = max(0, min(100, int(level)))
    if IS_LINUX and shutil.which("amixer"):
        subprocess.run(["amixer", "set", "Master", f"{level}%"], check=False, capture_output=True)
        return ToolResult.success(f"Volume set to {level}%")
    if IS_MAC:
        subprocess.run(["osascript", "-e", f"set volume output volume {level}"], check=False)
        return ToolResult.success(f"Volume set to {level}%")
    if IS_WINDOWS:
        return ToolResult.failure("On Windows install 'pycaw' to control volume (not bundled).")
    return ToolResult.failure("Volume control not available on this platform.")


@tool(
    "set_brightness",
    "Set screen brightness (0-100). Platform dependent.",
    {"type": "object", "properties": {"level": {"type": "integer"}}, "required": ["level"]},
    category="system",
)
def set_brightness(ctx: ToolContext, level: int) -> ToolResult:
    level = max(0, min(100, int(level)))
    if IS_LINUX and shutil.which("brightnessctl"):
        subprocess.run(["brightnessctl", "set", f"{level}%"], check=False, capture_output=True)
        return ToolResult.success(f"Brightness set to {level}%")
    return ToolResult.failure(
        "Brightness control needs a platform helper "
        "(brightnessctl on Linux, screen-brightness-control / WMI on Windows)."
    )


def get_tools() -> list[Tool]:
    return [
        get_datetime,
        get_cpu,
        get_ram,
        get_battery,
        list_processes,
        get_wifi_status,
        set_volume,
        set_brightness,
    ]
