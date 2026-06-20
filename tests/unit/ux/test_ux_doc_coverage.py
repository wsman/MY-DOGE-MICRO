"""Docs-consistency gate for the design/ux/ seed (Wave 2 docs).

Asserts the cross-cutting UX spec framework exists and is internally consistent
with the verified source anchors. This is a documentation-coverage test, not a
runtime test: it reads files on disk and fails loudly when the UX seed drifts
from what the code actually ships.

Scope (Wave 2 seed):
  - design/ux/README.md
  - design/ux/interaction-patterns.md
  - design/ux/accessibility-requirements.md
  - design/ux/scanner-flow.md

Out of scope (follow-on, expected absent): the per-flow specs for ticker,
archive, and analysis. Those are tracked as xfail below so the gate reminds the
next wave to add them without failing this seed run.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# Repository root: this file lives at <root>/tests/unit/ux/test_ux_doc_coverage.py
REPO_ROOT = Path(__file__).resolve().parents[3]
UX_DIR = REPO_ROOT / "design" / "ux"

# --- Required seed files ----------------------------------------------------

REQUIRED_SEED_FILES = [
    "README.md",
    "interaction-patterns.md",
    "accessibility-requirements.md",
    "scanner-flow.md",
]

# The six registered web views (web/src/types/splitTree.ts:22). Every view is
# expected to eventually have a per-flow spec. The Wave 2 seed ships the
# cross-cutting docs + scanner-flow only; the other three are follow-ons.
REGISTERED_VIEW_IDS = [
    "scanner",
    "cn-archive",
    "us-archive",
    "ticker",
    "insights",
    "analysis",
]


def _read(name: str) -> str:
    path = UX_DIR / name
    assert path.is_file(), f"missing required UX seed file: {path}"
    return path.read_text(encoding="utf-8")


# --- Seed existence ---------------------------------------------------------


def test_design_ux_directory_exists() -> None:
    """design/ux/ must exist (design/CLAUDE.md mandates it)."""
    assert UX_DIR.is_dir(), f"design/ux/ directory missing at {UX_DIR}"


@pytest.mark.parametrize("name", REQUIRED_SEED_FILES)
def test_required_seed_files_exist(name: str) -> None:
    """Each Wave 2 seed file named in the recon outline must exist."""
    _read(name)  # asserts existence + reads


# --- browserslist declaration ----------------------------------------------


def test_accessibility_requirements_declares_browserslist() -> None:
    """accessibility-requirements.md must declare a browserslist (vue-web-console.md
    §9.4 Open Question 6, closed at the spec level by this seed)."""
    text = _read("accessibility-requirements.md")
    assert "browserslist" in text, (
        "accessibility-requirements.md must declare a browserslist so the "
        "OffscreenCanvas/Intl.Segmenter runtime floors are documented"
    )
    # The declaration must name at least one concrete browser target, not just
    # the word "browserslist" in prose.
    assert re.search(r"Chrome|Edge|Firefox|Safari", text), (
        "browserslist declaration must name a concrete browser target"
    )


# --- interaction-patterns anchors (cite shipped reality) -------------------


def test_interaction_patterns_documents_watchdog() -> None:
    """interaction-patterns.md must document the SHIPPED 30s watchdog (S002-010)
    that resolves the stuck-running gap — not the pre-fix behavior."""
    text = _read("interaction-patterns.md")
    assert "watchdog" in text.lower(), (
        "interaction-patterns.md must document the SSE watchdog"
    )
    assert "30000" in text or "30s" in text or "30 second" in text.lower(), (
        "watchdog threshold (30000ms / 30s) must be cited"
    )
    assert "stream_stalled" in text, (
        "watchdog terminal error code 'stream_stalled' must be cited"
    )


def test_interaction_patterns_documents_shortcut_map() -> None:
    """The keyboard shortcut map (App.vue:24-74) must be cited."""
    text = _read("interaction-patterns.md")
    for shortcut in ["Ctrl+Shift+H", "Ctrl+Shift+V", "Ctrl+W", "Ctrl+Enter"]:
        assert shortcut in text, f"shortcut {shortcut} missing from the map"


def test_interaction_patterns_cites_ratio_clamp() -> None:
    """The split-tree ratio clamp 0.05-0.95 (useSplitTree.ts:26-27) must be cited."""
    text = _read("interaction-patterns.md")
    assert "0.05" in text and "0.95" in text, (
        "ratio clamp bounds (0.05-0.95) must be cited"
    )


def test_interaction_patterns_cites_vendored_pretext() -> None:
    """@pretext must be documented as vendored (S002-012), not as a sibling-project
    alias dependency."""
    text = _read("interaction-patterns.md")
    assert "vendored" in text.lower() or "vendor/pretext" in text, (
        "@pretext vendoring (S002-012) must be documented"
    )


# --- scanner-flow anchors ---------------------------------------------------


def test_scanner_flow_documents_terminal_error_banner() -> None:
    """scanner-flow.md must document the SHIPPED n-alert + Retry terminal-error
    banner (S002-010), not the stale 'error only in log' state."""
    text = _read("scanner-flow.md")
    assert "Retry" in text, "Retry affordance must be documented"
    assert "n-alert" in text, "terminal-error n-alert banner must be documented"
    # The status must NOT silently reset to idle on error.
    assert "not" in text.lower() and "idle" in text.lower(), (
        "scanner-flow must state the error status is NOT silently reset to idle"
    )


def test_scanner_flow_cites_sse_routes() -> None:
    """scanner-flow.md must cite the real scan API routes (src/doge/interfaces/api/routers/scan.py)."""
    text = _read("scanner-flow.md")
    assert "/api/scan/" in text, "scan SSE route must be cited"
    assert "servers/test" in text, "server test route must be cited"


# --- Per-flow coverage (follow-on reminder, expected-absent today) ----------


@pytest.mark.parametrize(
    "view_id, expected_spec",
    [
        ("scanner", "scanner-flow.md"),
        ("ticker", "ticker-flow.md"),
        ("cn-archive", "archive-flow.md"),
        ("us-archive", "archive-flow.md"),
        ("insights", "analysis-flow.md"),
        ("analysis", "analysis-flow.md"),
    ],
)
def test_each_view_has_a_flow_spec(view_id: str, expected_spec: str) -> None:
    """Every registered ViewId should eventually have a per-flow UX spec.

    The Wave 2 seed ships scanner-flow.md + the cross-cutting docs only; the
    ticker/archive/analysis specs are explicit follow-ons. Those are marked
    xfail so the gate reminds the next wave to add them without failing this
    seed run.
    """
    spec_path = UX_DIR / expected_spec
    if spec_path.is_file():
        return  # spec exists; pass
    if view_id == "scanner":
        pytest.fail(f"scanner must have a flow spec ({expected_spec}) in this seed")
    pytest.xfail(
        f"follow-on UX spec for view '{view_id}' not yet authored: "
        f"expected {expected_spec} (Wave 2 seed ships cross-cutting + scanner only)"
    )
