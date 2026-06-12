"""Forbidden-pattern grep-gate contract tests (S002-005 / TR-011 / TR-040).

These tests replicate the control-manifest §6 grep gates for the THREE sites
this story owns, plus the src/doge sys.path gate. They are contract tests
(grep over source text), not behavior tests — their job is to FAIL LOUDLY the
moment a forbidden pattern is reintroduced into one of the remediated files.

Scope (per orchestrator decisions #1-#4):
  - ``src/api/routers/scan.py`` is FREE of ``init_db_custom``,
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
# scan.py — interface-layer forbidden patterns (decision #1)
# ---------------------------------------------------------------------------
SCAN_PY = _SRC / "api" / "routers" / "scan.py"


class TestScanPyForbiddenPatterns:
    def test_no_init_db_custom_in_scan_py(self):
        # Arrange / Act
        hits = _grep_needles(SCAN_PY, ["init_db_custom"])
        # Assert
        assert hits == [], f"init_db_custom leaked into scan.py: {hits}"

    def test_no_sqlite3_import_or_connect_in_scan_py(self):
        hits = _grep_needles(SCAN_PY, ["import sqlite3", "sqlite3.connect"])
        assert hits == [], f"raw sqlite3 leaked into scan.py: {hits}"

    def test_no_connect_duckdb_in_scan_py(self):
        hits = _grep_needles(SCAN_PY, ["connect_duckdb"])
        assert hits == [], f"connect_duckdb leaked into scan.py: {hits}"

    def test_no_interface_layer_project_root_in_scan_py(self):
        # The interface layer must not recompute _PROJECT_ROOT.
        hits = _grep_needles(SCAN_PY, ["_PROJECT_ROOT"])
        assert hits == [], f"_PROJECT_ROOT leaked into scan.py: {hits}"

    def test_scan_py_grep_acceptance_gate_zero_hits(self):
        """The exact acceptance grep from orchestrator decision #1."""
        hits = _grep_needles(
            SCAN_PY,
            ["import sqlite3", "sqlite3.connect", "init_db_custom", "connect_duckdb"],
        )
        assert hits == [], f"scan.py acceptance gate FAILED: {hits}"


# ---------------------------------------------------------------------------
# momentum_scanner.py — get_connection sqlite3.connect gate (decision #2)
# ---------------------------------------------------------------------------
MOMENTUM_PY = _SRC / "micro" / "momentum_scanner.py"


class TestMomentumScannerGetConnectionGate:
    def test_no_raw_sqlite3_connect_in_momentum_scanner(self):
        """The file contains NO literal ``sqlite3.connect`` token anywhere.

        get_connection now routes through SQLiteConnection (clean adapter).
        """
        hits = _grep_needles(MOMENTUM_PY, ["sqlite3.connect"])
        assert hits == [], f"sqlite3.connect leaked into momentum_scanner.py: {hits}"

    def test_no_top_level_sqlite3_import_in_momentum_scanner(self):
        """No ``import sqlite3`` at module top (the adapter owns the import)."""
        hits = _grep_needles(MOMENTUM_PY, ["import sqlite3"])
        assert hits == [], f"import sqlite3 leaked into momentum_scanner.py: {hits}"

    def test_no_module_global_data_dir_recalculation_in_momentum_scanner(self):
        """The module-global ``current_dir``/``project_root``/``data_dir``
        _PROJECT_ROOT-style recalculation is gone (paths come from settings)."""
        # The legacy offending lines were:
        #   current_dir = os.path.dirname(os.path.abspath(__file__))
        #   project_root = os.path.dirname(os.path.dirname(current_dir))
        #   data_dir = os.path.join(project_root, 'data')
        hits = _grep_needles(
            MOMENTUM_PY,
            ["data_dir = os.path.join(project_root"],
        )
        assert hits == [], f"module-global data_dir recalc leaked: {hits}"

    def test_no_sys_path_manipulation_in_momentum_scanner(self):
        hits = _grep_needles(MOMENTUM_PY, ["sys.path.insert", "sys.path.append"])
        assert hits == [], f"sys.path manipulation leaked: {hits}"


# ---------------------------------------------------------------------------
# tdx_downloader.py — sys.path.insert / sibling-import gate (decision #3)
# ---------------------------------------------------------------------------
TDX_DOWNLOADER_PY = _SRC / "micro" / "tdx_downloader.py"


class TestTdxDownloaderSysPathGate:
    def test_no_sys_path_insert_in_tdx_downloader(self):
        hits = _grep_needles(TDX_DOWNLOADER_PY, ["sys.path.insert"])
        assert hits == [], f"sys.path.insert leaked into tdx_downloader.py: {hits}"

    def test_no_sys_path_append_in_tdx_downloader(self):
        hits = _grep_needles(TDX_DOWNLOADER_PY, ["sys.path.append"])
        assert hits == [], f"sys.path.append leaked into tdx_downloader.py: {hits}"

    def test_no_bare_sibling_database_import_in_tdx_downloader(self):
        """The shim-dependent ``from database import ...`` is now
        ``from micro.database import ...``."""
        hits = _grep_needles(TDX_DOWNLOADER_PY, ["from database import"])
        assert hits == [], f"bare 'from database import' leaked: {hits}"

    def test_no_bare_sibling_tdx_loader_import_in_tdx_downloader(self):
        hits = _grep_needles(TDX_DOWNLOADER_PY, ["from tdx_loader import"])
        assert hits == [], f"bare 'from tdx_loader import' leaked: {hits}"

    def test_no_project_root_recalc_in_tdx_downloader(self):
        hits = _grep_needles(TDX_DOWNLOADER_PY, ["_PROJECT_ROOT"])
        assert hits == [], f"_PROJECT_ROOT leaked into tdx_downloader.py: {hits}"


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
# src/api/ routers + main.py — interface-layer forbidden patterns (S003-003)
# ---------------------------------------------------------------------------
API_DIR = _SRC / "api"


class TestApiRouterForbiddenPatterns:
    """After S003-003 no src/api/ file imports sqlite3 or calls connect_duckdb."""

    def test_no_sqlite3_or_connect_duckdb_in_api_layer(self):
        """Broad §6 gate: src/api/**/*.py must be free of forbidden DB symbols."""
        hits = _grep_dir(
            [API_DIR],
            ["import sqlite3", "sqlite3.connect", "connect_duckdb"],
        )
        assert hits == [], f"forbidden DB pattern in src/api: {hits}"

    def test_api_deps_py_is_sanctioned_infra_site(self):
        """deps.py is allowed to import infrastructure via composition.py.

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
        "api/routers/scan.py",
        "api/routers/data.py",
        "api/routers/macro.py",
        "api/routers/analysis.py",
        "api/main.py",
        "doge/interfaces/api/deps.py",
        "micro/momentum_scanner.py",
        "micro/tdx_downloader.py",
    ],
)
def test_remediated_file_exists(rel):
    assert (_SRC / rel).exists(), f"{rel} missing after remediation"
