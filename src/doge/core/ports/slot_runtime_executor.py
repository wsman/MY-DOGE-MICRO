"""Port for slot runtime execution boundaries."""

from __future__ import annotations

from typing import Any, Callable, Protocol


class ISlotRuntimeExecutor(Protocol):
    """Executes slot-owned callables behind a runtime permission boundary."""

    available: bool
    executor_name: str

    def run(
        self,
        slot_id: str,
        permissions: Any,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Run ``func`` with the supplied slot identity and permissions."""


class DisabledSlotRuntimeExecutor:
    """Fail-closed executor used when slot runtime interception is disabled."""

    available = False
    executor_name = "disabled"
    disabled_reason = "Slot runtime interception is disabled by configuration."

    def run(
        self,
        slot_id: str,
        permissions: Any,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        raise RuntimeError(self.disabled_reason)
