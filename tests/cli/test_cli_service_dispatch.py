"""Service-dispatch unit tests for ``src/cli.py`` (BATCH-4 clean-architecture).

Asserts the four query subcommands (``stock`` / ``rsrs`` / ``breadth`` /
``anomaly``) delegate to their read-only service via the composition-root
``build_*_service`` factories — with NO DuckDB connection opened (the
testability gain BATCH-4 delivers). Each test:

  1. monkeypatches ``cli.build_*_service`` to return a FakeService that
     records the call args and returns canned rows,
  2. invokes the matching ``cmd_*`` handler with an argparse Namespace,
  3. asserts the right service method was called with the right args AND the
     formatted tabulate table was printed (behavior preservation), and
  4. asserts the no-data path prints the documented message and exits with
     the new distinct ``EXIT_NO_DATA`` (1) code (closes the
     docs/CLI.md-flagged gap).

Determinism: NO database / NO network — the service seam is the only entry
point exercised. The factories are the seam because the handlers call them
directly (``build_stock_service().query(...)``).
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

# Test-shim exception (documented in test_settings.py): make src/ importable.
# Mirrors the ``pythonpath=["src"]`` pytest config so this file also runs when
# invoked directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

# Load src/cli.py by explicit file path under a DISTINCT module name. A bare
# ``import cli`` would resolve to the ``tests/cli`` package (this directory's
# __init__.py), shadowing the target module — loading by spec avoids the name
# collision and guarantees we exercise src/cli.py specifically.
_CLI_PATH = Path(__file__).resolve().parents[2] / "src" / "cli.py"
_spec = importlib.util.spec_from_file_location("doge_cli_under_test", _CLI_PATH)
doge_cli = importlib.util.module_from_spec(_spec)
sys.modules["doge_cli_under_test"] = doge_cli
_spec.loader.exec_module(doge_cli)


# --------------------------------------------------------------------------- #
# Fakes — record calls, return canned records (List[dict], matching the
# service return shape; NO DuckDB / NO DataFrame ingestion at the CLI seam)
# --------------------------------------------------------------------------- #
class _FakeBase:
    """Records the single method call a handler makes (one service per cmd)."""

    def __init__(self, rows=None):
        self.calls = []          # list of (method_name, args, kwargs)
        self._rows = rows if rows is not None else []


class FakeStockService(_FakeBase):
    def query(self, ticker, market, days=20):
        self.calls.append(("query", (ticker, market, days), {}))
        return self._rows

    def overview(self, ticker, market):
        self.calls.append(("overview", (ticker, market), {}))
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


def _ns(**kw) -> argparse.Namespace:
    """Build an argparse.Namespace from kwargs (mirrors handler arg shape)."""
    return argparse.Namespace(**kw)


# --------------------------------------------------------------------------- #
# Helpers: monkeypatch the build_* factories on the cli module (the seam)
# --------------------------------------------------------------------------- #
def _patch_factory(monkeypatch, factory_name, fake_service):
    """Patch ``cli.<factory_name>`` to return ``fake_service`` (the seam)."""
    monkeypatch.setattr(doge_cli, factory_name, lambda *a, **kw: fake_service)
    return fake_service


# --------------------------------------------------------------------------- #
# cmd_stock — delegates to build_stock_service().query
# --------------------------------------------------------------------------- #
def test_cmd_stock_delegates_to_stock_service_query_and_formats_table(capsys, monkeypatch):
    # Arrange — canned CN enriched rows (the columns DuckDBStockRepository
    # returns for the cn market: date, open, ..., vol_20d).
    rows = [{
        "date": "2026-06-11", "open": 10.0, "high": 10.5, "low": 9.8,
        "close": 10.2, "volume": 1000, "ret_pct": 1.2, "ma_5": 10.1,
        "ma_10": 10.0, "ma_20": 9.9, "ma_60": 9.5, "atr14": 0.3,
        "ma60_dev": 0.7, "vol_20d": 0.4,
    }]
    fake = _patch_factory(monkeypatch, "build_stock_service", FakeStockService(rows))
    args = _ns(ticker="600000", market="cn", days=20)

    # Act
    doge_cli.cmd_stock(args)

    # Assert — delegated with NORMALIZED ticker + parsed args
    assert fake.calls == [("query", ("600000.SH", "cn", 20), {})]
    out = capsys.readouterr().out
    assert "date" in out and "600000.SH" not in out  # headers printed, rows formatted
    assert "10.20" in out  # close value rendered with .2f floatfmt


def test_cmd_stock_normalizes_bare_cn_code_before_dispatch(monkeypatch):
    # Arrange
    fake = _patch_factory(monkeypatch, "build_stock_service", FakeStockService([{"date": "x"}]))
    args = _ns(ticker="301599", market="cn", days=5)

    # Act
    doge_cli.cmd_stock(args)

    # Assert — bare 3xx code normalized to .SZ before reaching the service
    assert fake.calls[0][1][0] == "301599.SZ"
    assert fake.calls[0][1] == ("301599.SZ", "cn", 5)


def test_cmd_stock_no_data_prints_message_and_exits_nonzero(capsys, monkeypatch):
    # Arrange — service returns no rows
    _patch_factory(monkeypatch, "build_stock_service", FakeStockService([]))
    args = _ns(ticker="UNKNOWN.SZ", market="cn", days=20)

    # Act / Assert — distinct exit code (closes docs/CLI.md-flagged gap)
    with pytest.raises(SystemExit) as exc:
        doge_cli.cmd_stock(args)
    assert exc.value.code == doge_cli.EXIT_NO_DATA == 1
    out = capsys.readouterr().out
    assert "no data for UNKNOWN.SZ" in out


# --------------------------------------------------------------------------- #
# cmd_rsrs — delegates to build_ranking_service().rsrs
# --------------------------------------------------------------------------- #
def test_cmd_rsrs_delegates_to_ranking_service_rsrs_and_formats_table(capsys, monkeypatch):
    # Arrange — canned ranking rows including the optional pct_change_60d column.
    # NOTE: ``rank`` / ``avg_vol_20d`` are floats to match the DuckDB view dtype;
    # tabulate's positional floatfmt only applies to float-typed columns, so an
    # int rank would shift the formatting positions and is not representative.
    rows = [{
        "rank": 1.0, "ticker": "600000.SH", "rsrs": 0.923456,
        "avg_vol_20d": 1000.0, "last_close": 10.2, "pct_change_60d": 5.4,
    }]
    fake = _patch_factory(monkeypatch, "build_ranking_service", FakeRankingService(rows))
    args = _ns(market="cn", top=20)

    # Act
    doge_cli.cmd_rsrs(args)

    # Assert
    assert fake.calls == [("rsrs", ("cn", 20), {})]
    out = capsys.readouterr().out
    assert "rank" in out and "ticker" in out and "600000.SH" in out
    # The floatfmt list is identical to the legacy handler, so the rendered
    # table is byte-for-byte the same behavior (verified by reproducing the
    # tabulate call with this fixture). Assert the headers + a formatted
    # value to confirm tabulate ran over the service rows.
    assert "last_close" in out and "10.20" in out


def test_cmd_rsrs_no_data_prints_message_and_exits_nonzero(capsys, monkeypatch):
    # Arrange
    _patch_factory(monkeypatch, "build_ranking_service", FakeRankingService([]))
    args = _ns(market="cn", top=20)

    # Act / Assert
    with pytest.raises(SystemExit) as exc:
        doge_cli.cmd_rsrs(args)
    assert exc.value.code == doge_cli.EXIT_NO_DATA
    assert "no data" in capsys.readouterr().out


# --------------------------------------------------------------------------- #
# cmd_breadth — delegates to build_breadth_service().breadth
# --------------------------------------------------------------------------- #
def test_cmd_breadth_delegates_to_breadth_service_breadth_and_formats_table(capsys, monkeypatch):
    # Arrange — canned breadth rows
    rows = [{
        "date": "2026-06-11", "advancers": 2100, "decliners": 1900,
        "avg_pct_change": 0.5, "up_ratio": 52.5,
    }]
    fake = _patch_factory(monkeypatch, "build_breadth_service", FakeBreadthService(rows))
    args = _ns(market="cn", days=10)

    # Act
    doge_cli.cmd_breadth(args)

    # Assert
    assert fake.calls == [("breadth", ("cn", 10), {})]
    out = capsys.readouterr().out
    assert "date" in out and "2026-06-11" in out


def test_cmd_breadth_no_data_prints_message_and_exits_nonzero(capsys, monkeypatch):
    # Arrange
    _patch_factory(monkeypatch, "build_breadth_service", FakeBreadthService([]))
    args = _ns(market="cn", days=10)

    # Act / Assert
    with pytest.raises(SystemExit) as exc:
        doge_cli.cmd_breadth(args)
    assert exc.value.code == doge_cli.EXIT_NO_DATA
    assert "no data" in capsys.readouterr().out


# --------------------------------------------------------------------------- #
# cmd_anomaly — delegates to build_anomaly_service().anomalies
# --------------------------------------------------------------------------- #
def test_cmd_anomaly_delegates_to_anomaly_service_anomalies_and_formats_table(capsys, monkeypatch):
    # Arrange — canned anomaly rows (cols returned by AnomalyService)
    rows = [{
        "ticker": "600000.SH", "date": "2026-06-11", "volume": 50000,
        "avg_vol": 10000, "vol_ratio": 5.0, "ret_pct": 2.1,
    }]
    fake = _patch_factory(monkeypatch, "build_anomaly_service", FakeAnomalyService(rows))
    args = _ns(min_ratio=3.0, top=20)

    # Act
    doge_cli.cmd_anomaly(args)

    # Assert
    assert fake.calls == [("anomalies", (3.0, 20), {})]
    out = capsys.readouterr().out
    assert "ticker" in out and "600000.SH" in out


def test_cmd_anomaly_forwards_custom_min_ratio_and_top(monkeypatch):
    # Arrange
    fake = _patch_factory(monkeypatch, "build_anomaly_service", FakeAnomalyService([{"ticker": "x"}]))
    args = _ns(min_ratio=5.5, top=50)

    # Act
    doge_cli.cmd_anomaly(args)

    # Assert — custom args forwarded unchanged
    assert fake.calls == [("anomalies", (5.5, 50), {})]


def test_cmd_anomaly_no_data_prints_message_and_exits_nonzero(capsys, monkeypatch):
    # Arrange
    _patch_factory(monkeypatch, "build_anomaly_service", FakeAnomalyService([]))
    args = _ns(min_ratio=3.0, top=20)

    # Act / Assert — distinct message preserved ("no anomalies found")
    with pytest.raises(SystemExit) as exc:
        doge_cli.cmd_anomaly(args)
    assert exc.value.code == doge_cli.EXIT_NO_DATA
    assert "no anomalies found" in capsys.readouterr().out


# --------------------------------------------------------------------------- #
# Seam invariant — handlers call the factories (NOT infrastructure directly)
# --------------------------------------------------------------------------- #
def test_cli_module_imports_no_duckdb_or_ai_analysis_symbols():
    """ADR-0001 forbidden-pattern gate: the CLI must not import connect_duckdb,
    query_sql, or anything from the legacy ``ai_analysis`` package; all DB
    access flows through the composition-root service factories."""
    import inspect

    src = Path(inspect.getfile(doge_cli)).read_text(encoding="utf-8")
    assert "from ai_analysis" not in src, (
        "cli.py still imports from the legacy ai_analysis package — forbidden"
    )
    assert "connect_duckdb" not in src, (
        "cli.py still references connect_duckdb — must delegate via services"
    )
    assert "query_sql" not in src
    assert "sys.path.insert" not in src, (
        "cli.py still has a sys.path.insert shim — pip install -e . removed the need"
    )
    # The four factories ARE imported (the seam the handlers call).
    for factory in (
        "build_stock_service",
        "build_ranking_service",
        "build_breadth_service",
        "build_anomaly_service",
    ):
        assert factory in src, f"cli.py must import {factory} from the composition root"
