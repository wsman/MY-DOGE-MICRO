"""Tests for the ``demo`` CLI subcommand (S006-007 / S007-003).

The demo command delegates to the same service seam as the other subcommands.
These tests verify argument parsing, handler dispatch, and no-data behavior
without requiring a running database.
"""
import argparse
import sys
from unittest.mock import MagicMock

import pytest

from doge.interfaces.cli.commands import demo as demo_cmd


def _make_args(market="cn", top=5):
    return argparse.Namespace(market=market, top=top)


class TestDemoCommand:
    def test_demo_exits_no_data_when_all_queries_empty(self, monkeypatch):
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
            demo_cmd.cmd_demo(_make_args())
        assert exc.value.code == demo_cmd.EXIT_NO_DATA

    def test_demo_prints_output_when_data_present(self, monkeypatch, capsys):
        ranking = [{"rank": 1, "ticker": "A", "rsrs": 1.0,
                    "avg_vol_20d": 100, "last_close": 10.0}]
        breadth = [{"date": "2026-01-01", "advancers": 100, "decliners": 50,
                    "advance_ratio": 0.66}]
        anomalies = [{"ticker": "B", "vol_ratio": 5.0}]
        stock = [{"date": "2026-01-01", "close": 10.0}]

        monkeypatch.setattr(
            demo_cmd, "build_ranking_service",
            lambda: MagicMock(rsrs=lambda _m, _t: ranking),
        )
        monkeypatch.setattr(
            demo_cmd, "build_breadth_service",
            lambda: MagicMock(breadth=lambda _m, days=0: breadth),
        )
        monkeypatch.setattr(
            demo_cmd, "build_anomaly_service",
            lambda: MagicMock(anomalies=lambda min_ratio=0, top=0: anomalies),
        )
        monkeypatch.setattr(
            demo_cmd, "build_stock_service",
            lambda: MagicMock(query=lambda _t, _m, days=0: stock),
        )

        demo_cmd.cmd_demo(_make_args())

        captured = capsys.readouterr()
        assert "MY-DOGE-MICRO 5-Minute Demo" in captured.out
        assert "A" in captured.out
        assert "Demo complete" in captured.out

    def test_demo_uses_us_sample_ticker_for_us_market(self, monkeypatch, capsys):
        query_mock = MagicMock(return_value=[{"date": "2026-01-01", "close": 1.0}])
        monkeypatch.setattr(
            demo_cmd, "build_ranking_service",
            lambda: MagicMock(rsrs=lambda _m, _t: []),
        )
        monkeypatch.setattr(
            demo_cmd, "build_breadth_service",
            lambda: MagicMock(breadth=lambda _m, days=0: []),
        )
        monkeypatch.setattr(
            demo_cmd, "build_anomaly_service",
            lambda: MagicMock(anomalies=lambda min_ratio=0, top=0: []),
        )
        monkeypatch.setattr(
            demo_cmd, "build_stock_service",
            lambda: MagicMock(query=query_mock),
        )

        demo_cmd.cmd_demo(_make_args(market="us"))

        query_mock.assert_called_once()
        # First positional arg is the ticker; for US market it should be AAPL.
        assert query_mock.call_args[0][0] == "AAPL"
        assert query_mock.call_args[0][1] == "us"

    def test_demo_parser_has_demo_subcommand(self):
        """The argparse setup includes a 'demo' subparser."""
        from doge.interfaces.cli.main import build_parser
        parser = build_parser()
        assert "demo" in parser._subparsers._group_actions[0].choices
