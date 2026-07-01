"""Regression tests: scanner path tolerates missing optional opentdx extra.

S003-002 blocker: ``opentdx`` is declared as an optional ``[tdx]`` extra in
``pyproject.toml``, but ``micro.tdx_downloader`` imported it unconditionally at
module top. Any path that imported ``tdx_downloader`` (including
``market_scanner`` and the FastAPI scan router) crashed with
``ModuleNotFoundError`` before the existing local-file fallback could run.

These tests simulate a clean Python process where ``opentdx`` is absent by
removing it from ``sys.modules`` (and any already-imported ``micro`` modules)
before importing the code under test.
"""
import sys
import types
from pathlib import Path

import pytest

# Make src/ importable for the test process (matches other micro tests).
MICRO_DIR = Path(__file__).resolve().parents[3] / "src"
if str(MICRO_DIR) not in sys.path:
    sys.path.insert(0, str(MICRO_DIR))

_MICRO_CHILDREN = (
    "database",
    "industry_analyzer",
    "market_scanner",
    "momentum_scanner",
    "tdx_downloader",
    "tdx_loader",
)


def _sync_micro_package_children() -> None:
    """Keep ``micro.<child>`` attributes aligned with ``sys.modules``."""
    micro_pkg = sys.modules.get("micro")
    if micro_pkg is None:
        return
    for child in _MICRO_CHILDREN:
        full_name = f"micro.{child}"
        module = sys.modules.get(full_name)
        if module is None:
            if hasattr(micro_pkg, child):
                delattr(micro_pkg, child)
        else:
            setattr(micro_pkg, child, module)


@pytest.fixture
def _no_opentdx(monkeypatch):
    """Simulate an environment where the optional opentdx extra is not installed."""
    # Snapshot and remove opentdx and micro modules so the import chain re-runs.
    to_remove = [
        m for m in sys.modules
        if m == "opentdx" or m.startswith("opentdx.") or m.startswith("micro.")
    ]
    saved = {m: sys.modules.pop(m) for m in to_remove}
    _sync_micro_package_children()

    # Ensure any future import of opentdx fails deterministically.
    original_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__

    def _blocking_import(name, *args, **kwargs):
        if name == "opentdx" or name.startswith("opentdx."):
            raise ModuleNotFoundError(f"No module named '{name}'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", _blocking_import)

    yield

    # Restore modules so other tests that mock opentdx continue to work.
    for name, mod in saved.items():
        sys.modules[name] = mod
    for name in list(sys.modules):
        if name == "opentdx" or name.startswith("opentdx.") or name.startswith("micro."):
            if name not in saved:
                sys.modules.pop(name, None)
    _sync_micro_package_children()


class TestTdxDownloaderWithoutOpentdx:
    def test_imports_and_exposes_public_surface(self, _no_opentdx):
        # Act
        import micro.tdx_downloader as tdx

        # Assert
        assert hasattr(tdx, "CN_SERVERS")
        assert hasattr(tdx, "US_SERVERS")
        assert hasattr(tdx, "find_working_server")
        assert hasattr(tdx, "download_cn_kline")
        assert hasattr(tdx, "download_us_kline")
        assert len(tdx.CN_SERVERS) > 0
        assert len(tdx.US_SERVERS) > 0

    def test_find_working_server_returns_none_when_opentdx_missing(self, _no_opentdx):
        # Arrange
        import micro.tdx_downloader as tdx

        # Act
        client, host = tdx.find_working_server(tdx.US_SERVERS, "us")

        # Assert
        assert client is None
        assert host is None


class TestMarketScannerWithoutOpentdx:
    def test_imports_without_crashing(self, _no_opentdx):
        # Act
        import micro.market_scanner as ms

        # Assert
        assert hasattr(ms, "MarketScanner")
        assert hasattr(ms, "_tdx_server_sync")

    def test_tdx_server_sync_falls_back_gracefully(self, _no_opentdx, tmp_path, capsys):
        # Arrange
        import micro.market_scanner as ms

        # Act
        result = ms._tdx_server_sync(str(tmp_path / "market.db"), market="us")

        # Assert
        assert result is False
        captured = capsys.readouterr()
        assert "opentdx not available" in captured.out


class TestScanRouterWithoutOpentdx:
    def test_router_imports_without_crashing(self, _no_opentdx):
        # Act
        from doge.interfaces.api.routers import scan

        # Assert
        assert hasattr(scan, "router")
        assert hasattr(scan, "start_scan")
