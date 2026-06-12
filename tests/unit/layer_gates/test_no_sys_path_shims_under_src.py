"""Forbidden-pattern grep-gate: NO ``sys.path`` shims under ``src/``.

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
  - The canonical repo-root MCP entrypoint (``doge_mcp.py``) must also contain
    no ``sys.path`` manipulation. Batch-6 deleted the legacy monolith and the
    old entrypoint carve-out.

Determinism: pure filesystem grep — no network, no DB, no imports.
"""
from pathlib import Path

import pytest

# Repo root is two parents above this test file
# (tests/unit/layer_gates/<this>.py -> tests/unit/layer_gates -> tests/unit -> tests -> repo root).
_REPO_ROOT = Path(__file__).resolve().parents[3]
_SRC = _REPO_ROOT / "src"

_FORBIDDEN_NEEDLES = ("sys.path.insert", "sys.path.append")


def _grep_src_for_sys_path_shims() -> list[str]:
    """Return ``file:lineno: line`` for every forbidden ``sys.path`` shim hit.

    Walks every ``.py`` under ``src/``.
    """
    hits: list[str] = []
    if not _SRC.exists():
        return hits
    for py in _SRC.rglob("*.py"):
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

    def test_root_doge_mcp_entrypoint_has_no_sys_path_shim(self):
        """The canonical MCP entrypoint relies on editable/package install."""
        entrypoint = _REPO_ROOT / "doge_mcp.py"
        assert entrypoint.exists(), "doge_mcp.py is the canonical MCP entrypoint"
        text = entrypoint.read_text(encoding="utf-8")
        hits = [
            needle
            for needle in _FORBIDDEN_NEEDLES
            if needle in text
        ]
        assert hits == [], (
            "doge_mcp.py must not reintroduce a sys.path compatibility shim; "
            "install the package/editable project instead. Found: "
            + ", ".join(hits)
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
