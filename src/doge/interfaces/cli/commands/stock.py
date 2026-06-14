"""CLI command: stock."""

import sys

import pandas as pd

from doge.application.composition import build_stock_service
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
