"""Deterministic smoke test for the PyQt6 desktop dashboard (Module #10).

This is an ADVISORY-gate smoke test per the testing standards: PyQt6 is a
desktop-only dependency that may be absent (or un-importable on a headless /
DLL-mismatched box). The test therefore MUST:

  * Force the Qt offscreen platform via ``QT_QPA_PLATFORM=offscreen`` BEFORE any
    PyQt6 import (so no real display is required).
  * Use ``pytest.importorskip("PyQt6")`` so a clean "not installed" env skips.
  * Additionally skip with a clear reason if PyQt6 is installed but its native
    DLLs fail to load (common on headless Windows without the matching MSVC
    runtime / Qt plugin path). A construct-failure of ``CommandCenter`` is NOT
    an acceptable skip reason -- only an import-time environment problem is.

Determinism: no network, no live market data writes. ``CommandCenter.__init__``
opens the three local SQLite databases via ``QSqlDatabase`` (read/write model)
and constructs four tabs; on a missing DB the ``QSqlTableModel`` simply returns
no rows and the editor stays empty -- it does not raise. The window is closed
immediately after construction so no Qt event loop runs.

Run: ``python -m pytest tests/test_pyqt_smoke.py -q``
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# 1. Force the offscreen Qt platform BEFORE importing PyQt6.
#    This must happen at module import time, before any PyQt6.QtWidgets import,
#    so that QGuiApplication does not try to open a real display.
# ---------------------------------------------------------------------------
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# ---------------------------------------------------------------------------
# 2. Make the src/interface/ directory importable the same way dashboard.py
#    expects (it does sibling imports: ``from scanner_gui import ScannerWidget``).
#    src/interface/ has no __init__.py today, so a plain path append matches the
#    real runtime layout exactly.
# ---------------------------------------------------------------------------
_INTERFACE_DIR = str(Path(__file__).resolve().parents[1] / "src" / "interface")
if _INTERFACE_DIR not in sys.path:
    sys.path.insert(0, _INTERFACE_DIR)


def _pyqt6_is_importable() -> bool:
    """Return True iff PyQt6.QtWidgets can actually be imported in this env.

    PyQt6 may be listed as installed (``pip show PyQt6``) but still fail at
    ``import PyQt6.QtWidgets`` when its native Qt6 DLLs cannot load -- common on
    headless Windows without the matching MSVC runtime or with a stale plugin
    path. We probe that here so the test skips rather than errors.
    """
    try:
        import PyQt6.QtWidgets  # noqa: F401
    except ImportError:
        return False
    return True


# ---------------------------------------------------------------------------
# 3. pytest.importorskip handles the clean "not installed" case; the in-body
#    import-skip below handles the "installed but DLLs won't load" case.
# ---------------------------------------------------------------------------
pytest.importorskip("PyQt6", reason="PyQt6 not installed -- desktop dashboard is ADVISORY-gate only")


def test_command_center_constructs_without_raising(qapp) -> None:
    """The top-level ``CommandCenter`` QMainWindow constructs and closes cleanly.

    This exercises:
      * Tab assembly (ScannerWidget, three DBEditorWidget tabs, AnalysisWidget)
      * Signal wiring (``scan_started_signal`` / ``scan_finished_signal``)
      * The local SQLite database open path via ``QSqlDatabase``

    A successful construct-then-close proves the dashboard's static structure is
    sound and that the four interface modules import and instantiate against the
    local-first data layout without raising.
    """
    # Imported here (not at module top) so the fixture-level skip fires first.
    from dashboard import CommandCenter

    window = CommandCenter()
    try:
        assert window.windowTitle() == "MY-DOGE QUANT SYSTEM"
        # The dashboard wires exactly five tabs in __init__ (dashboard.py:58-82).
        assert window.tabs.count() == 5
    finally:
        window.close()


# ---------------------------------------------------------------------------
# Fixture: a shared QApplication for the test session. QtWidgets requires
# exactly one QApplication per process; constructing one per test would raise.
# We build it lazily so module-level collection does not require a display.
#
# PyQt6 may be installed yet unable to load its native DLLs on a headless box
# (Windows MSVC runtime / Qt plugin path mismatch). That is an environment
# problem, not a dashboard defect -- we skip cleanly so the ADVISORY gate never
# breaks CI. A construct-failure of ``CommandCenter`` is NOT covered by this
# skip; that would surface as a real test error.
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def qapp():
    if not _pyqt6_is_importable():
        pytest.skip(
            "PyQt6 is installed but its native Qt6 DLLs cannot load in this "
            "environment (headless / DLL-mismatch). Desktop dashboard smoke is "
            "ADVISORY-gate only."
        )

    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv[:1])
    yield app
