import pytest

from doge.application.agent.state_machine import InvalidRunStatusTransition, ensure_transition
from doge.core.domain.agent_models import RunStatus


def test_state_machine_valid_transitions():
    ensure_transition(RunStatus.CREATED, RunStatus.QUEUED)
    ensure_transition(RunStatus.QUEUED, RunStatus.RUNNING)
    ensure_transition(RunStatus.RUNNING, RunStatus.AWAITING_APPROVAL)
    ensure_transition(RunStatus.AWAITING_APPROVAL, RunStatus.QUEUED)
    ensure_transition(RunStatus.CANCELLING, RunStatus.CANCELLED)


def test_state_machine_rejects_terminal_transition():
    with pytest.raises(InvalidRunStatusTransition):
        ensure_transition(RunStatus.COMPLETED, RunStatus.RUNNING)
