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

#: Pseudo-label used when no run exists yet (mirrors the Web "Idle" label).
IDLE_LABEL = "Idle"


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
