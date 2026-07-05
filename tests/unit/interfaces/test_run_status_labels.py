"""Pin the CLI run-status label map to the RunStatus enum.

Sprint UX-1 Slice A (WEB-2). The label map at
``doge.interfaces.cli.run_status_labels`` must enumerate exactly the 8
``RunStatus`` members defined at ``doge.core.domain.agent_models.RunStatus``,
so that adding a backend status forces a label update here (and in the Web
twin) instead of silently falling through to the "Status: <raw>" fallback.
"""

from __future__ import annotations

from doge.core.domain.agent_models import RunStatus
from doge.interfaces.cli.run_status_labels import (
    IDLE_LABEL,
    RUN_STATUS_LABELS,
    label_for_run_status,
)


def test_label_map_covers_every_run_status_member_exactly() -> None:
    """RUN_STATUS_LABELS keys are exactly the RunStatus enum values."""
    enum_values = {member.value for member in RunStatus}
    labeled_values = set(RUN_STATUS_LABELS)
    assert enum_values == labeled_values, (
        "RunStatus enum and RUN_STATUS_LABELS diverged: "
        f"missing={sorted(enum_values - labeled_values)} "
        f"extra={sorted(labeled_values - enum_values)}"
    )


def test_known_statuses_have_non_default_labels() -> None:
    """Each member maps to a real label, not the fallback form."""
    for member in RunStatus:
        label = label_for_run_status(member.value)
        assert label != f"Status: {member.value}"
        assert label


def test_idle_and_unknown_fallbacks() -> None:
    assert label_for_run_status(None) == IDLE_LABEL
    assert label_for_run_status("") == IDLE_LABEL
    assert (
        label_for_run_status(RunStatus.AWAITING_APPROVAL.value)
        == "Waiting on your approval"
    )
    assert label_for_run_status("future_status") == "Status: future_status"
