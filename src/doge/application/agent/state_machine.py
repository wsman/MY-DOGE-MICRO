"""State-transition rules for agent runs."""

from __future__ import annotations

from doge.core.domain.agent_models import RunStatus


VALID_TRANSITIONS: dict[RunStatus, set[RunStatus]] = {
    RunStatus.CREATED: {RunStatus.QUEUED, RunStatus.RUNNING, RunStatus.CANCELLING, RunStatus.FAILED},
    RunStatus.QUEUED: {RunStatus.RUNNING, RunStatus.CANCELLING, RunStatus.CANCELLED, RunStatus.FAILED},
    RunStatus.RUNNING: {
        RunStatus.AWAITING_APPROVAL,
        RunStatus.CANCELLING,
        RunStatus.CANCELLED,
        RunStatus.COMPLETED,
        RunStatus.FAILED,
    },
    RunStatus.AWAITING_APPROVAL: {
        RunStatus.QUEUED,
        RunStatus.RUNNING,
        RunStatus.CANCELLING,
        RunStatus.CANCELLED,
        RunStatus.FAILED,
    },
    RunStatus.CANCELLING: {RunStatus.CANCELLED, RunStatus.FAILED},
    RunStatus.CANCELLED: set(),
    RunStatus.COMPLETED: set(),
    RunStatus.FAILED: set(),
}


class InvalidRunStatusTransition(ValueError):
    """Raised when a run status transition violates the state machine."""


def can_transition(current: RunStatus, target: RunStatus) -> bool:
    return target == current or target in VALID_TRANSITIONS[current]


def ensure_transition(current: RunStatus, target: RunStatus) -> None:
    if not can_transition(current, target):
        raise InvalidRunStatusTransition(f"invalid run status transition: {current.value} -> {target.value}")
