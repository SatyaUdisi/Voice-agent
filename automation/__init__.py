"""Cross-cutting automation concerns: platform detection and permissions."""

from automation.permissions import PermissionManager
from automation.platform import PlatformInfo, current_platform

__all__ = ["PermissionManager", "PlatformInfo", "current_platform"]
