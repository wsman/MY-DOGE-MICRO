"""CLI command: stock."""

import sys

import pandas as pd

from doge.bootstrap import build_gateway_container
from doge.interfaces.cli.constants import EXIT_NO_DATA
from doge.interfaces.cli.formatters import fmt_stock_table
from doge.interfaces.cli.normalize import normalize_ticker


def cmd_stock(args) -> None:
    """Query OHLCV + indicators for a ticker via StockService."""
    market = args.market
    ticker = normalize_ticker(args.ticker, market)
    data = build_stock_service().query(ticker, market, args.days)

    if not data:
        print(f"no data for {args.ticker}")
        sys.exit(EXIT_NO_DATA)

    df = pd.DataFrame(data)
    print(fmt_stock_table(df))


def _gateway_container():
    return build_gateway_container()


def build_stock_service():
    return _gateway_container().build_stock_service()
