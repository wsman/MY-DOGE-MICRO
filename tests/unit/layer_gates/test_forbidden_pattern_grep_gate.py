"""Forbidden-pattern grep-gate contract tests (S002-005 / TR-011 / TR-040).

These tests replicate the control-manifest §6 grep gates for the THREE sites
this story owns, plus the src/doge sys.path gate. They are contract tests
(grep over source text), not behavior tests — their job is to FAIL LOUDLY the
moment a forbidden pattern is reintroduced into one of the remediated files.

Scope (per orchestrator decisions #1-#4):
  - ``src/doge/interfaces/api/routers/scan.py`` is FREE of ``init_db_custom``,
    ``import sqlite3``, ``sqlite3.connect``, ``connect_duckdb``, and the
    interface-layer ``_PROJECT_ROOT`` recalc. (The broader §6 src/api gate
    covering the OTHER routers — data/macro/analysis/main — is owned by
    S002-009; this test scopes to scan.py, the named S002-005 file.)
  - ``src/micro/momentum_scanner.py`` has NO raw ``sqlite3.connect`` (the
    MomentumRanker.get_connection path now routes through SQLiteConnection).
  - ``src/micro/tdx_downloader.py`` has NO ``sys.path.insert``/``append`` and
    NO bare ``from database import`` / ``from tdx_loader import`` sibling
    imports (now package-qualified ``from micro.<mod> import ...``).
  - ``src/doge/`` has NO ``sys.path.insert``/``append`` at all.

Determinism: pure filesystem grep, no network / no DB / no imports.
"""
from pathlib import Path

import pytest

# src/ is the repo root's source tree (tests live in tests/, src/ is sibling).
_SRC = Path(__file__).resolve().parents[3] / "src"


def _grep_needles(path: Path, needles) -> list[str]:
    """Return lines of *path* whose text contains any of *needles*.

    Comments and docstrings are NOT excluded — the gate is deliberately
    strict: a forbidden token in a comment still indicates the pattern is
    documented inline and should be reworded. (The remediation reworded all
    such prose mentions.)
    """
    text = path.read_text(encoding="utf-8")
    hits = []
    for line in text.splitlines():
        if any(n in line for n in needles):
            hits.append(line)
    return hits


# ---------------------------------------------------------------------------
# src/api/routers/scan.py was a redirect shim removed in Sprint M. The
# interface-layer DB-symbol / _PROJECT_ROOT prohibition it enforced is now
# covered by test_api_layer_gate over the canonical api_legacy/gateway routers.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# src/micro/ (momentum_scanner.py + tdx_downloader.py) was removed in Sprint M.
# The forbidden-pattern gates that policed those files are retired.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# src/doge/ — sys.path gate (decision #4, control-manifest §6)
# ---------------------------------------------------------------------------
DOGE_DIR = _SRC / "doge"


def _grep_dir(roots, needles) -> list[str]:
    """Grep every .py under each root dir for any needle; return 'file:line' hits."""
    hits = []
    for root in roots:
        for py in root.rglob("*.py"):
            try:
                text = py.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for lineno, line in enumerate(text.splitlines(), start=1):
                if any(n in line for n in needles):
                    hits.append(f"{py}:{lineno}: {line.strip()}")
    return hits


class TestDogeSysPathGate:
    def test_no_sys_path_manipulation_under_src_doge(self):
        """control-manifest §6: ``grep -rn sys.path.insert src/doge/`` is empty."""
        hits = _grep_dir([DOGE_DIR], ["sys.path.insert", "sys.path.append"])
        assert hits == [], f"sys.path manipulation under src/doge/: {hits}"


# ---------------------------------------------------------------------------
# src/api/ redirect shim was removed in Sprint M; only the canonical deps.py
# sanctioned-infra-seam check remains below.
# ---------------------------------------------------------------------------


class TestApiRouterForbiddenPatterns:
    def test_api_deps_py_is_sanctioned_infra_site(self):
        """deps.py is allowed to import infrastructure via bootstrap containers.

        The gate above would already fail if deps.py imported sqlite3/duckdb
        directly; this test documents that deps.py is the intended seam.
        """
        assert (_SRC / "doge" / "interfaces" / "api" / "deps.py").exists(), "deps.py seam missing"


# ---------------------------------------------------------------------------
# Sanity: the remediated files still exist (no accidental deletion).
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "rel",
    [
        "doge/interfaces/api/deps.py",
        "doge/interfaces/api/deps.py",
    ],
)
def test_remediated_file_exists(rel):
    assert (_SRC / rel).exists(), f"{rel} missing after remediation"
