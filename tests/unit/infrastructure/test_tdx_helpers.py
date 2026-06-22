import sys
from types import SimpleNamespace

import pandas as pd

from doge.infrastructure.data_source import tdx_helpers


def test_ticker_to_market_code_maps_cn_suffixes(monkeypatch):
    market = SimpleNamespace(SH=object(), SZ=object(), BJ=object())
    monkeypatch.setitem(sys.modules, "opentdx", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "opentdx.const", SimpleNamespace(MARKET=market))

    assert tdx_helpers.ticker_to_market_code("600000.SH") == (market.SH, "600000")
    assert tdx_helpers.ticker_to_market_code("000001.SZ") == (market.SZ, "000001")
    assert tdx_helpers.ticker_to_market_code("430047.BJ") == (market.BJ, "430047")


def test_bars_to_df_normalizes_cn_and_us_date_columns():
    cn = tdx_helpers.bars_to_df(
        [
            {
                "datetime": pd.Timestamp("2026-06-10"),
                "open": 10.0,
                "high": 11.0,
                "low": 9.5,
                "close": 10.5,
                "vol": 1000,
                "amount": 1.0,
            }
        ],
        "600000.SH",
    )
    us = tdx_helpers.bars_to_df(
        [
            {
                "date_time": pd.Timestamp("2026-06-10"),
                "open": 100.0,
                "high": 110.0,
                "low": 99.0,
                "close": 105.0,
                "vol": 2000,
                "amount": 2.0,
            }
        ],
        "AAPL",
    )

    assert cn is not None
    assert us is not None
    assert list(cn.columns) == ["date", "open", "high", "low", "close", "volume", "amount", "ticker"]
    assert cn.iloc[0]["date"] == "2026-06-10"
    assert us.iloc[0]["ticker"] == "AAPL"


def test_find_working_server_degrades_without_opentdx(monkeypatch):
    original_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__

    def _blocking_import(name, *args, **kwargs):
        if name == "opentdx" or name.startswith("opentdx."):
            raise ModuleNotFoundError(f"No module named '{name}'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", _blocking_import)

    assert tdx_helpers.find_working_server(["127.0.0.1"], "cn") == (None, None)
