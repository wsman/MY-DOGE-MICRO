"""Forbidden-pattern grep-gate: NO ``sys.path`` shims anywhere under ``src/``.

S002-009 / TR-011 (Batch-1): the editable install (``pip install -e .``) makes
``micro``, ``macro``, ``ai_analysis``, ``api``, ``interface``, and ``doge``
importable as TOP-LEVEL packages. Every legacy
``sys.path.insert`` / ``sys.path.append`` + ``_PROJECT_ROOT`` dirname-walk shim
under ``src/`` has been removed in favour of package-qualified sibling imports
(``from micro.X import`` etc.) and path derivation via ``get_settings()``.

This is a CONTRACT test (grep over source text), not a behaviour test. Its job
is to FAIL LOUDLY the moment a ``sys.path`` manipulation is reintroduced into
any module under ``src/`` — that pattern is an ADR-0001 forbidden pattern
(``sys_path_insert`` / ``sys_path_append``) because it papered over a missing
package install and made import order machine-dependent.

Scope:
  - ``src/**`` must contain ZERO ``sys.path.insert`` / ``sys.path.append``
    occurrences.
  - The two tolerated COMPAT ENTRYPOINTS (``mcp_server.py`` and
    ``doge_mcp.py``) live at the REPO ROOT, NOT under ``src/``, so the
    ``src/``-scoped gate naturally excludes them. They are removed in Batch-6.
    As a defensive belt-and-braces, the gate ALSO tolerates those two
    filenames by basename (so the test stays correct even if a future
    refactor relocates them).

Determinism: pure filesystem grep — no network, no DB, no imports.
"""
from pathlib import Path

import pytest

# Repo root is two parents above this test file
# (tests/unit/layer_gates/<this>.py -> tests/unit/layer_gates -> tests/unit -> tests -> repo root).
_REPO_ROOT = Path(__file__).resolve().parents[3]
_SRC = _REPO_ROOT / "src"

# The two tolerated compat entrypoints (Batch-6 owns their removal). These live
# at repo root today; matched by basename so the test is robust to relocation.
_TOLERATED_ENTRYPOINTS = {"mcp_server.py", "doge_mcp.py"}

_FORBIDDEN_NEEDLES = ("sys.path.insert", "sys.path.append")


def _grep_src_for_sys_path_shims() -> list[str]:
    """Return ``file:lineno: line`` for every forbidden ``sys.path`` shim hit.

    Walks every ``.py`` under ``src/``. Hits inside the two tolerated
    entrypoints (by basename) are excluded even though those files are not
    under ``src/`` today — defensive against future relocation.
    """
    hits: list[str] = []
    if not _SRC.exists():
        return hits
    for py in _SRC.rglob("*.py"):
        if py.name in _TOLERATED_ENTRYPOINTS:
            continue
        try:
            text = py.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if any(needle in line for needle in _FORBIDDEN_NEEDLES):
                hits.append(f"{py}:{lineno}: {line.strip()}")
    return hits


class TestNoSysPathShimsUnderSrc:
    def test_no_sys_path_insert_or_append_anywhere_under_src(self):
        """ADR-0001 forbidden pattern: ``src/`` contains ZERO sys.path shims.

        The editable install (``pip install -e .``) resolves
        ``micro`` / ``macro`` / ``ai_analysis`` / ``api`` / ``interface`` /
        ``doge`` as top-level packages, so the legacy
        ``sys.path.insert`` / ``sys.path.append`` + ``_PROJECT_ROOT`` walks are
        obsolete. If this test fails, a shim was reintroduced: rewrite the
        sibling import package-qualified (``from micro.X import``) and source
        any derived paths from ``get_settings()``.
        """
        # Arrange / Act
        hits = _grep_src_for_sys_path_shims()
        # Assert
        assert hits == [], (
            "sys.path.insert/append shims found under src/ (ADR-0001 forbidden "
            "pattern). Rewrite as package-qualified imports + get_settings():\n"
            + "\n".join(hits)
        )

    @pytest.mark.parametrize(
        "rel",
        [
            "micro/market_scanner.py",
            "micro/industry_analyzer.py",
            "ai_analysis/anomaly_detection.py",
            "ai_analysis/catalog_generator.py",
            "ai_analysis/fetch_names.py",
            "ai_analysis/market_overview.py",
            "ai_analysis/stock_notes.py",
            "macro/cli.py",
            "interface/analysis_gui.py",
            "interface/dashboard.py",
            "interface/scanner_gui.py",
            "api/main.py",
            "api/routers/data.py",
            "api/routers/macro.py",
            "api/routers/analysis.py",
            "api/routers/config.py",
        ],
    )
    def test_remediated_module_still_exists(self, rel):
        """Sanity: no remediated file was accidentally deleted."""
        assert (_SRC / rel).exists(), f"{rel} missing after Batch-1 remediation"


# ---------------------------------------------------------------------------
# Tolerated-entrypoint sanity: the two compat shims still live at repo root
# (Batch-6 removes them). This sub-test DOCUMENTS the carve-out and will start
# FAILING once Batch-6 lands — at which point Batch-6 should delete this class.
# ---------------------------------------------------------------------------
class TestToleratedEntrypointsStillPresent:
    @pytest.mark.parametrize("name", sorted(_TOLERATED_ENTRYPOINTS))
    def test_entrypoint_exists_at_repo_root(self, name):
        """mcp_server.py / doge_mcp.py are the ONLY tolerated sys.path shims.

        They are NOT under ``src/`` so the ``src/`` gate above excludes them.
        This test exists so Batch-6 (which removes them) knows to also delete
        this carve-out documentation. If you are seeing this fail because the
        file moved INTO ``src/``, the ``src/`` gate will catch the shim first.
        """
        assert (_REPO_ROOT / name).exists(), (
            f"{name} removed from repo root — Batch-6 done? Delete this "
            "TestToleratedEntrypointsStillPresent class and drop the basename "
            "tolerance in _grep_src_for_sys_path_shims."
        )
