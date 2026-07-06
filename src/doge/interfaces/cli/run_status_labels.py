"""CLI-facing human labels for RunStatus values.

Sprint UX-1 Slice A (WEB-2). Single source of truth for run-status wording on
the CLI side. Mirrors the Web util at ``web/src/utils/runStatus.ts``; both are
pinned to the 8 ``RunStatus`` members defined at
``doge.core.domain.agent_models.RunStatus`` so a backend enum change is caught
by ``tests/unit/interfaces/test_run_status_labels.py``.

Replaces ad-hoc status string handling in the CLI REPL (e.g. the planned
``/status`` command in Slice D and ``doge doctor --next`` in Slice C) so the
CLI and Web render the same vocabulary.
"""

from __future__ import annotations

from typing import Mapping

from doge.core.domain.agent_models import RunStatus

#: ``RunStatus`` value -> human label. Tones intentionally mirror the Web
#: util's Naive-UI mapping (success/error/warning/info/default) so a status
#: reads identically across surfaces.
RUN_STATUS_LABELS: Mapping[str, str] = {
    RunStatus.CREATED.value: "Preparing",
    RunStatus.QUEUED.value: "Queued",
    RunStatus.RUNNING.value: "Running",
    RunStatus.AWAITING_APPROVAL.value: "Waiting on your approval",
    RunStatus.CANCELLING.value: "Cancelling",
    RunStatus.CANCELLED.value: "Cancelled",
    RunStatus.COMPLETED.value: "Completed",
    RunStatus.FAILED.value: "Failed",
}

#: ``RunStatus`` value -> operator-facing next-action hints. This is kept
#: parallel to ``RUN_STATUS_LABELS`` and pinned by the same enum coverage test.
RUN_STATUS_NEXT_ACTIONS: Mapping[str, tuple[str, ...]] = {
    RunStatus.CREATED.value: ("Wait for worker",),
    RunStatus.QUEUED.value: ("Wait for worker",),
    RunStatus.RUNNING.value: ("Watch live",),
    RunStatus.AWAITING_APPROVAL.value: ("Approve or deny",),
    RunStatus.CANCELLING.value: ("Wait for cancel",),
    RunStatus.CANCELLED.value: ("Re-queue or discard",),
    RunStatus.COMPLETED.value: ("Open artifacts",),
    RunStatus.FAILED.value: ("Inspect error", "Re-run"),
}

#: Pseudo-label used when no run exists yet (mirrors the Web "Idle" label).
IDLE_LABEL = "Idle"

#: Safe hints for statuses that are not real ``RunStatus`` members.
IDLE_NEXT_ACTIONS = ("Start a run",)
UNKNOWN_STATUS_NEXT_ACTIONS = ("Check run details",)


def label_for_run_status(status: str | None) -> str:
    """Return the human label for a run status.

    ``None`` or an empty string (no run yet) maps to ``"Idle"``. Unknown values
    fall through to ``"Status: <raw>"`` so future statuses surface rather than
    hide behind a wrong label.
    """
    if not status:
        return IDLE_LABEL
    label = RUN_STATUS_LABELS.get(status)
    if label is not None:
        return label
    return f"Status: {status}"


def next_actions_for_run_status(status: str | None) -> tuple[str, ...]:
    """Return operator-facing next actions for a run status.

    Idle and unknown values use safe fallbacks so non-enum statuses such as
    ``data_unavailable`` do not appear to be supported backend states.
    """
    if not status:
        return IDLE_NEXT_ACTIONS
    actions = RUN_STATUS_NEXT_ACTIONS.get(status)
    if actions is not None:
        return actions
    return UNKNOWN_STATUS_NEXT_ACTIONS
