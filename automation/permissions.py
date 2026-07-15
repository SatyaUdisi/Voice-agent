"""Automation permission gating.

Centralises the policy for whether automation is enabled at all and whether a
destructive action requires user confirmation. The GUI can supply an interactive
confirmation callback; headless/test contexts can auto-allow or auto-deny.
"""

from __future__ import annotations

from collections.abc import Callable

ConfirmFn = Callable[[str], bool]


class PermissionManager:
    """Decides whether tool actions may proceed."""

    def __init__(
        self,
        *,
        automation_enabled: bool = True,
        confirm_destructive: bool = True,
        confirm_fn: ConfirmFn | None = None,
    ) -> None:
        self._automation_enabled = automation_enabled
        self._confirm_destructive = confirm_destructive
        self._confirm_fn = confirm_fn

    @property
    def automation_enabled(self) -> bool:
        return self._automation_enabled

    def set_confirm_fn(self, fn: ConfirmFn | None) -> None:
        self._confirm_fn = fn

    def confirm(self, prompt: str) -> bool:
        """Return whether an action is permitted.

        If confirmations are disabled, allow. Otherwise defer to the supplied
        confirmation callback; if none is set, deny by default (fail safe).
        """
        if not self._automation_enabled:
            return False
        if not self._confirm_destructive:
            return True
        if self._confirm_fn is None:
            return False
        return bool(self._confirm_fn(prompt))
