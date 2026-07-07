"""Runtime event watcher middleware for slot-contributed watchers."""

from __future__ import annotations

from typing import Iterable

from doge.core.domain.agent_models import AgentEvent
from doge.platform.slots import (
    SlotConfigurationError,
    SlotContext,
    WatcherContribution,
    WatcherDecision,
)

_ALLOWED_ACTIONS = {"allow", "warn", "pause", "block", "fail"}
_BLOCKING_ACTIONS = {"pause", "block", "fail"}


class WatcherDecisionError(RuntimeError):
    """Raised when a watcher blocks a runtime event before transaction commit."""

    def __init__(
        self,
        *,
        watcher_id: str,
        action: str,
        reason: str,
        approval_required: bool = False,
    ) -> None:
        self.watcher_id = watcher_id
        self.action = action
        self.reason = reason
        self.approval_required = approval_required
        detail = reason or "no reason provided"
        super().__init__(f"watcher {watcher_id} returned {action}: {detail}")


class RuntimeEventWatcherMiddleware:
    """Evaluate watcher contributions for each persisted runtime event."""

    def __init__(
        self,
        watchers: Iterable[WatcherContribution],
        context: SlotContext,
    ) -> None:
        self._watchers = tuple(watchers)
        if not self._watchers:
            raise ValueError("RuntimeEventWatcherMiddleware requires at least one watcher")
        self._context = context

    def decisions_for(self, event: AgentEvent) -> tuple[tuple[str, WatcherDecision], ...]:
        """Return watcher decisions that apply to ``event`` without enforcing them."""

        decisions: list[tuple[str, WatcherDecision]] = []
        event_type = _event_type_value(event)
        for watcher in self._watchers:
            if watcher.event_types and event_type not in watcher.event_types:
                continue
            decisions.append((watcher.watcher_id, _safe_decision(watcher, event, self._context)))
        return tuple(decisions)

    def enforce(self, event: AgentEvent) -> None:
        """Raise before commit when a watcher returns a blocking decision."""

        for watcher_id, decision in self.decisions_for(event):
            action = decision.action.strip().lower()
            if action not in _ALLOWED_ACTIONS:
                raise SlotConfigurationError(
                    f"watcher {watcher_id} returned unsupported action: {decision.action!r}"
                )
            if action in _BLOCKING_ACTIONS:
                raise WatcherDecisionError(
                    watcher_id=watcher_id,
                    action=action,
                    reason=decision.reason,
                    approval_required=decision.approval_required,
                )


def _safe_decision(
    watcher: WatcherContribution,
    event: AgentEvent,
    context: SlotContext,
) -> WatcherDecision:
    try:
        decision = watcher.on_event(event, context)
    except Exception as exc:  # noqa: BLE001 - watcher failures must fail closed
        raise WatcherDecisionError(
            watcher_id=watcher.watcher_id,
            action="fail",
            reason=f"watcher raised: {exc}",
        ) from exc
    if decision is None:
        raise SlotConfigurationError(f"watcher {watcher.watcher_id} returned no decision")
    return decision


def _event_type_value(event: AgentEvent) -> str:
    value = event.event_type
    return value.value if hasattr(value, "value") else str(value)
