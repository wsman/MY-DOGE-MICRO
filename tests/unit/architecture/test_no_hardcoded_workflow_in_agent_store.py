"""Repo grep gate: no hard-coded workflow literal in the agent store (UX-1 Slice G).

After the ScenarioPicker lands, the agent store must source the run workflow from
``selectedScenarioSlug`` rather than re-introducing the legacy
``'investment_research'`` literal. This reads the store source and asserts the
literal is gone.
"""

from __future__ import annotations

import re
from pathlib import Path

# tests/unit/architecture/test_no_hardcoded_workflow_in_agent_store.py -> repo root.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_STORE = _REPO_ROOT / "web" / "src" / "stores" / "agent.ts"


def test_no_hardcoded_investment_research_literal_in_agent_store() -> None:
    text = _STORE.read_text(encoding="utf-8")
    # Match the literal only as a quoted string (single or double quotes).
    matches = re.findall(r"'investment_research'|\"investment_research\"", text)
    assert not matches, (
        "web/src/stores/agent.ts must source workflow from selectedScenarioSlug, "
        "not re-introduce the 'investment_research' literal (UX-1 Slice G). "
        f"Found {len(matches)} occurrence(s)."
    )
