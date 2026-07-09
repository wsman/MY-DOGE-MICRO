"""Tests for ``doge.interfaces.cli`` service dispatch and exit codes."""

import argparse
import sys
from io import StringIO
from unittest.mock import MagicMock

import pytest

from doge.interfaces.cli import main
from doge.interfaces.cli.commands import (
    anomaly as anomaly_cmd,
    breadth as breadth_cmd,
    demo as demo_cmd,
    rsrs as rsrs_cmd,
    stock as stock_cmd,
)
from doge.interfaces.cli.constants import EXIT_NO_DATA


class _FakeBase:
    def __init__(self, rows=None):
        self.calls = []
        self._rows = rows if rows is not None else []


class FakeStockService(_FakeBase):
    def query(self, ticker, market, days=20):
        self.calls.append(("query", (ticker, market, days), {}))
        return self._rows


class FakeRankingService(_FakeBase):
    def rsrs(self, market="cn", top=20):
        self.calls.append(("rsrs", (market, top), {}))
        return self._rows


class FakeBreadthService(_FakeBase):
    def breadth(self, market="cn", days=10):
        self.calls.append(("breadth", (market, days), {}))
        return self._rows


class FakeAnomalyService(_FakeBase):
    def anomalies(self, min_ratio=3.0, top=20):
        self.calls.append(("anomalies", (min_ratio, top), {}))
        return self._rows


def _ns(**kw):
    return argparse.Namespace(**kw)


def _patch_factory(monkeypatch, module, factory_name, fake_service):
    monkeypatch.setattr(module, factory_name, lambda *a, **kw: fake_service)
    return fake_service


class TestStockCommand:
    def test_delegates_to_stock_service(self, capsys, monkeypatch):
        rows = [{"date": "2026-06-11", "open": 10.0, "high": 10.5, "low": 9.8,
                 "close": 10.2, "volume": 1000}]
        fake = _patch_factory(monkeypatch, stock_cmd, "build_stock_service", FakeStockService(rows))
        stock_cmd.cmd_stock(_ns(ticker="600000", market="cn", days=20))
        assert fake.calls == [("query", ("600000.SH", "cn", 20), {})]
        assert "10.20" in capsys.readouterr().out

    def test_no_data_exits_nonzero(self, capsys, monkeypatch):
        _patch_factory(monkeypatch, stock_cmd, "build_stock_service", FakeStockService([]))
        with pytest.raises(SystemExit) as exc:
            stock_cmd.cmd_stock(_ns(ticker="UNKNOWN", market="cn", days=20))
        assert exc.value.code == EXIT_NO_DATA


class TestRsrsCommand:
    def test_delegates_to_ranking_service(self, capsys, monkeypatch):
        rows = [{"rank": 1, "ticker": "A", "rsrs": 0.9,
                 "avg_vol_20d": 100, "last_close": 10.0}]
        fake = _patch_factory(monkeypatch, rsrs_cmd, "build_ranking_service", FakeRankingService(rows))
        rsrs_cmd.cmd_rsrs(_ns(market="cn", top=20))
        assert fake.calls == [("rsrs", ("cn", 20), {})]
        assert "last_close" in capsys.readouterr().out

    def test_no_data_exits_nonzero(self, monkeypatch):
        _patch_factory(monkeypatch, rsrs_cmd, "build_ranking_service", FakeRankingService([]))
        with pytest.raises(SystemExit) as exc:
            rsrs_cmd.cmd_rsrs(_ns(market="cn", top=20))
        assert exc.value.code == EXIT_NO_DATA


class TestBreadthCommand:
    def test_delegates_to_breadth_service(self, capsys, monkeypatch):
        rows = [{"date": "2026-06-11", "advancers": 100, "decliners": 50}]
        fake = _patch_factory(monkeypatch, breadth_cmd, "build_breadth_service", FakeBreadthService(rows))
        breadth_cmd.cmd_breadth(_ns(market="cn", days=10))
        assert fake.calls == [("breadth", ("cn", 10), {})]
        assert "2026-06-11" in capsys.readouterr().out

    def test_no_data_exits_nonzero(self, monkeypatch):
        _patch_factory(monkeypatch, breadth_cmd, "build_breadth_service", FakeBreadthService([]))
        with pytest.raises(SystemExit) as exc:
            breadth_cmd.cmd_breadth(_ns(market="cn", days=10))
        assert exc.value.code == EXIT_NO_DATA


class TestAnomalyCommand:
    def test_delegates_to_anomaly_service(self, capsys, monkeypatch):
        rows = [{"ticker": "A", "vol_ratio": 5.0}]
        fake = _patch_factory(monkeypatch, anomaly_cmd, "build_anomaly_service", FakeAnomalyService(rows))
        anomaly_cmd.cmd_anomaly(_ns(min_ratio=3.0, top=20))
        assert fake.calls == [("anomalies", (3.0, 20), {})]
        assert "A" in capsys.readouterr().out

    def test_no_data_exits_nonzero(self, monkeypatch):
        _patch_factory(monkeypatch, anomaly_cmd, "build_anomaly_service", FakeAnomalyService([]))
        with pytest.raises(SystemExit) as exc:
            anomaly_cmd.cmd_anomaly(_ns(min_ratio=3.0, top=20))
        assert exc.value.code == EXIT_NO_DATA


class TestDemoCommand:
    def test_exits_no_data_when_all_empty(self, monkeypatch):
        for svc_name in ("build_ranking_service", "build_breadth_service",
                         "build_anomaly_service", "build_stock_service"):
            monkeypatch.setattr(
                demo_cmd,
                svc_name,
                lambda _name=svc_name: MagicMock(**{
                    "rsrs.return_value": [],
                    "breadth.return_value": [],
                    "anomalies.return_value": [],
                    "query.return_value": [],
                }),
            )
        with pytest.raises(SystemExit) as exc:
            demo_cmd.cmd_demo(_ns(market="cn", top=5))
        assert exc.value.code == EXIT_NO_DATA

    def test_prints_output_when_data_present(self, monkeypatch, capsys):
        monkeypatch.setattr(demo_cmd, "build_ranking_service",
                            lambda: MagicMock(rsrs=lambda _m, _t: [{"rank": 1, "ticker": "A", "rsrs": 0.9, "avg_vol_20d": 100, "last_close": 10.0}]))
        monkeypatch.setattr(demo_cmd, "build_breadth_service",
                            lambda: MagicMock(breadth=lambda _m, days=0: [{"date": "x", "advancers": 1, "decliners": 1, "avg_pct_change": 0.0, "up_ratio": 0.0}]))
        monkeypatch.setattr(demo_cmd, "build_anomaly_service",
                            lambda: MagicMock(anomalies=lambda min_ratio=0, top=0: [{"ticker": "B", "vol_ratio": 5.0}]))
        monkeypatch.setattr(demo_cmd, "build_stock_service",
                            lambda: MagicMock(query=lambda _t, _m, days=0: [{"date": "x", "close": 1.0}]))
        demo_cmd.cmd_demo(_ns(market="cn", top=5))
        out = capsys.readouterr().out
        assert "OpenDoge 5-Minute Demo" in out
        assert "Demo complete" in out


class TestMainEntrypoint:
    def test_main_prints_help_when_no_subcommand(self, capsys):
        main([])
        out = capsys.readouterr().out
        assert "usage: doge" in out
        assert "stock" in out
        assert "macro" in out

    def test_main_dispatches_stock(self, monkeypatch, capsys):
        calls = []
        import importlib
        main_mod = importlib.import_module("doge.interfaces.cli.main")
        monkeypatch.setattr(main_mod, "cmd_stock", lambda args: calls.append(args))
        main(["stock", "AAPL", "--market", "us", "--days", "10"])
        assert len(calls) == 1
        assert calls[0].ticker == "AAPL"
        assert calls[0].market == "us"
        assert calls[0].days == 10

    def test_invalid_market_exits_2(self):
        with pytest.raises(SystemExit) as exc:
            main(["stock", "AAPL", "--market", "hk"])
        assert exc.value.code == 2


class TestCliLayerGate:
    def test_canonical_cli_imports_no_legacy_surface(self):
        """doge.interfaces.cli commands must not import micro/macro/ai_analysis."""
        import inspect
        from pathlib import Path

        import doge.interfaces.cli as cli_pkg

        pkg_path = Path(inspect.getfile(cli_pkg)).parent
        legacy_api = "src.api"
        forbidden = ["from micro", "import micro", "from ai_analysis", "import ai_analysis",
                     "from macro", "import macro",
                     f"from {legacy_api}", f"import {legacy_api}",
                     "from src.interface", "import src.interface"]
        for source_path in pkg_path.rglob("*.py"):
            text = source_path.read_text(encoding="utf-8")
            for pattern in forbidden:
                assert pattern not in text, (
                    f"{source_path.relative_to(pkg_path)} imports legacy surface: {pattern}"
                )

    def test_canonical_cli_imports_no_duckdb_or_sqlite(self):
        """doge.interfaces.cli commands must not import sqlite3/duckdb directly."""
        import inspect
        from pathlib import Path

        import doge.interfaces.cli as cli_pkg

        pkg_path = Path(inspect.getfile(cli_pkg)).parent
        for source_path in pkg_path.rglob("*.py"):
            text = source_path.read_text(encoding="utf-8")
            assert "import sqlite3" not in text, f"{source_path.name} imports sqlite3"
            assert "import duckdb" not in text, f"{source_path.name} imports duckdb"
