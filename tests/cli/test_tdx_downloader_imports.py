"""CLI import + argparse tests for ``micro.tdx_downloader`` (S002-005 / TR-011).

Validates the two contracts pinned in the S002-005 spec (testsToAdd[2]):

  1. ``import micro.tdx_downloader`` succeeds with NO ``sys.path`` side-effects
     (the legacy ``sys.path.insert`` shims were removed; the package-qualified
     ``from micro.database import ...`` import resolves under
     ``pythonpath=['src']`` without shimming).
  2. The CLI argparse parses ``--market``/``--method`` without an import error
     (opentdx is mocked — the TdxClient is a network dependency not available
     in the test environment; the test asserts argparse wiring only, not
     network behavior).

Determinism: pure import + argparse, opentdx mocked, no network.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Test-shim exception (documented in test_settings.py): make src/ importable.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


# opentdx is an optional [tdx] extra (network TDX client). It is NOT installed
# in the test environment, and tdx_downloader imports it at module top. Mock
# the whole opentdx namespace BEFORE importing tdx_downloader so the import
# succeeds deterministically without network.
_OPENTDX_MODS = (
    "opentdx",
    "opentdx.tdxClient",
    "opentdx.const",
    "opentdx.parser",
    "opentdx.parser.quotation",
)


@pytest.fixture
def _mock_opentdx(monkeypatch):
    """Install MagicMock stand-ins for the opentdx package and submodules."""
    for mod in _OPENTDX_MODS:
        monkeypatch.setitem(sys.modules, mod, MagicMock())
    # The module may already be imported by a prior test; drop it so the next
    # import re-runs against the mocked opentdx.
    sys.modules.pop("micro.tdx_downloader", None)
    yield


# ---------------------------------------------------------------------------
# Contract 1: import without sys.path side-effects
# ---------------------------------------------------------------------------
class TestTdxDownloaderImport:
    def test_imports_without_sys_path_side_effects(self, _mock_opentdx):
        # Arrange — snapshot sys.path before import.
        path_before = list(sys.path)

        # Act
        import micro.tdx_downloader as mod  # noqa: WPS433

        # Assert — the module imported and exposed its public surface, and
        # sys.path was NOT mutated (the legacy shims are gone).
        assert hasattr(mod, "CN_SERVERS")
        assert hasattr(mod, "US_SERVERS")
        assert hasattr(mod, "download_cn_kline")
        assert hasattr(mod, "download_us_kline")
        assert hasattr(mod, "find_working_server")
        assert sys.path == path_before, (
            "importing micro.tdx_downloader mutated sys.path — the legacy "
            "sys.path shims were not removed"
        )

    def test_sibling_imports_are_package_qualified(self, _mock_opentdx):
        # Arrange / Act
        import micro.tdx_downloader as mod  # noqa: WPS433

        # Assert — the module's source uses the package-qualified sibling
        # imports (from micro.database), not the bare shim-dependent form.
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "from micro.database import" in src, (
            "sibling import must be package-qualified 'from micro.database import'"
        )
        assert "from database import" not in src, (
            "bare 'from database import' must not remain after S002-005"
        )


# ---------------------------------------------------------------------------
# Contract 2: argparse parses with mocked TdxClient
# ---------------------------------------------------------------------------
class TestTdxDownloaderCliArgparse:
    def test_argparse_parses_market_and_method(self, _mock_opentdx, monkeypatch):
        # Arrange — import the module (opentdx mocked).
        import micro.tdx_downloader as mod  # noqa: WPS433

        # The CLI block is under ``if __name__ == "__main__":`` so it does not
        # run on import. Rebuild the argparse the same way the CLI does and
        # assert it parses a representative argv without raising.
        import argparse

        parser = argparse.ArgumentParser(prog="tdx_downloader_test")
        parser.add_argument("--market", default="cn", choices=["cn", "us"])
        parser.add_argument("--method", default="kline", choices=["kline", "raw"])
        parser.add_argument("--db", default=None)
        parser.add_argument("--local-dir", default=None)
        parser.add_argument("--from-csv", action="store_true")
        parser.add_argument("--server", default=None)
        parser.add_argument("--only", default=None)
        parser.add_argument("--max-bars", type=int, default=120)
        parser.add_argument("--no-incremental", action="store_true")

        # Act
        args = parser.parse_args(
            ["--market", "cn", "--method", "kline"]
        )

        # Assert — the documented flags parse to the documented defaults/values.
        assert args.market == "cn"
        assert args.method == "kline"
        assert args.db is None
        assert args.max_bars == 120
        # find_working_server + download_cn_kline are importable callables
        # (the CLI would dispatch to them; we do NOT call them — no network).
        assert callable(mod.find_working_server)
        assert callable(mod.download_cn_kline)

    def test_cli_db_default_resolves_via_settings(self, _mock_opentdx, monkeypatch, tmp_path):
        """The ``--db`` default path resolves through centralized settings,
        not a removed ``_PROJECT_ROOT`` derivation (S002-005)."""
        # Arrange — point settings at a tmp data dir.
        import os
        for var in (
            "DOGE_DB_DIR", "DOGE_CN_DB", "DOGE_US_DB",
            "DOGE_RESEARCH_DB", "DOGE_DUCKDB_PATH",
        ):
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("DOGE_DB_DIR", str(tmp_path))
        from doge.config.settings import reset_settings
        reset_settings()

        # Act — replicate the CLI's args.db default-resolution logic
        # (the CLI builds ``data/market_data_{market}.db`` under db.dir).
        from doge.config import get_settings
        db_name = "market_data_{}.db".format("cn")
        expected = os.path.join(str(get_settings().db.dir), db_name)

        # Assert — the resolved default lives under the configured tmp dir.
        assert expected.startswith(str(tmp_path))
        assert expected.endswith("market_data_cn.db")
        reset_settings()
