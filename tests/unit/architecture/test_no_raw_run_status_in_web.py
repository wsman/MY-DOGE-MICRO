"""Repo grep gate: no raw run-status enum literals in the migrated Web views.

Sprint UX-1 Slice A (WEB-2). After the run-status label map
(``web/src/utils/runStatus.ts``) lands, the migrated Web views must render
status through it rather than re-introducing hard-coded enum strings. This test
reads the view sources and asserts none of the ``RunStatus`` values (plus the
``idle`` pseudo-status) appear as quoted literals.

The util itself (``runStatus.ts``) is intentionally NOT scanned — it is the one
allowed home for those literals. Test/fixture files are not scanned either; they
legitimately use status values as inputs.
"""

from __future__ import annotations

import re
from pathlib import Path

# tests/unit/architecture/test_no_raw_run_status_in_web.py -> repo root.
_REPO_ROOT = Path(__file__).resolve().parents[3]

# Views that render run / execution status. RunDetailView is included as a
# regression guard even though it shows coverage/claims/citations (no run
# status today) — if it ever grows a run-status display, this gate catches it.
_WEB_VIEWS = [
    "web/src/views/ResearchAgentView.vue",
    "web/src/components/case/ExecutionMonitor.vue",
    "web/src/views/RunDetailView.vue",
]

# RunStatus values (agent_models.py:19-27) plus the "idle" pseudo-status.
_BANNED_VALUES = [
    "created",
    "queued",
    "running",
    "awaiting_approval",
    "cancelling",
    "cancelled",
    "completed",
    "failed",
    "idle",
]


def test_no_raw_run_status_literals_in_web_views() -> None:
    for rel in _WEB_VIEWS:
        text = (_REPO_ROOT / rel).read_text(encoding="utf-8")
        for value in _BANNED_VALUES:
            # Match the value only as a quoted string literal (single or double
            # quotes) so plain-English uses of words like "running" elsewhere in
            # the template do not false-positive.
            pattern = re.compile(rf"'{re.escape(value)}'|\"{re.escape(value)}\"")
            matches = pattern.findall(text)
            assert not matches, (
                f"{rel}: raw run-status literal {value!r} must render via "
                f"web/src/utils/runStatus.ts, not be hard-coded (UX-1 Slice A). "
                f"Found {len(matches)} occurrence(s)."
            )
