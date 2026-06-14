"""
MY-DOGE CLI — 股票数据查询工具

Usage:
    python src/cli.py stock <ticker> [--market cn] [--days 20]
    python src/cli.py rsrs [--market cn] [--top 20]
    python src/cli.py breadth [--market cn] [--days 10]
    python src/cli.py anomaly [--min-ratio 3.0] [--top 20]
    python src/cli.py demo [--market cn] [--top 5]

Clean-architecture wiring (ADR-0001 / ADR-0010): each subcommand delegates to
its read-only service via the composition root factories in
``doge.core.services.composition``. This file contains NO inline SQL and opens
NO DuckDB connections directly — the ``build_*`` factories inject the wired
``DuckDBMarketViewRepository`` / ``DuckDBStockRepository`` adapters. The
service seam is what makes the command handlers unit-testable without a
database (see ``tests/cli/test_cli_service_dispatch.py``).

Exit codes:
    0  success (including help when no subcommand is given)
    1  query returned no rows for the supplied filter
    2  argparse rejection (invalid flag / value)
"""

import argparse
import re
import sys

import pandas as pd
from tabulate import tabulate

from doge.core.services.composition import (
    build_anomaly_service,
    build_breadth_service,
    build_ranking_service,
    build_stock_service,
)

# Distinct exit code for the "no data" case (docs/CLI.md flagged the prior
# gap of returning 0 on no data as tech debt). Chosen so it does not collide
# with argparse's exit 2 or the implicit success exit 0.
EXIT_NO_DATA = 1


def normalize_ticker(ticker: str, market: str = "cn") -> str:
    """Normalize a bare CN code to its exchange-suffixed ticker.

    CN: ``6xx``/``68x`` -> ``.SH``, ``0xx``/``3xx`` -> ``.SZ``,
    ``4xx``/``8xx`` -> ``.BJ``. Non-CN markets and codes already containing a
    suffix are returned unchanged.

    This is a local copy of the helper that lived in ``ai_analysis`` so the CLI
    no longer imports from the legacy package (the MCP ``query_stock`` tool
    keeps an identical local copy). Raises ``ValueError`` on malformed input.
    """
    if not isinstance(ticker, str):
        raise ValueError("ticker must be a string")
    code = ticker.strip()
    if not code:
        raise ValueError("ticker cannot be empty")
    if len(code) > 20:
        raise ValueError("ticker too long (max 20 chars)")
    if not re.match(r"^[A-Za-z0-9.\\-]+$", code):
        raise ValueError("ticker contains invalid characters")

    if market != "cn" or "." in code:
        return code
    if code[0] == "6":
        return f"{code}.SH"
    elif code[0] in ("0", "3"):
        return f"{code}.SZ"
    elif code[0] in ("4", "8"):
        return f"{code}.BJ"
    return code


def cmd_stock(args):
    """Query OHLCV + indicators for a ticker via StockService.

    Formats the same tabulate table as the legacy inline-SQL handler; the
    "no data" case prints the same message and now exits with code
    :data:`EXIT_NO_DATA` (1) instead of the prior implicit 0.
    """
    market = args.market
    ticker = normalize_ticker(args.ticker, market)
    data = build_stock_service().query(ticker, market, args.days)

    if not data:
        print(f"no data for {args.ticker}")
        sys.exit(EXIT_NO_DATA)

    df = pd.DataFrame(data)
    print(tabulate(df, headers="keys", tablefmt="simple", showindex=False,
                   floatfmt=(".0f", ".2f", ".2f", ".2f", ".2f", ".0f")))


def cmd_rsrs(args):
    """Query the RSRS momentum ranking via RankingService."""
    data = build_ranking_service().rsrs(args.market, args.top)

    if not data:
        print("no data")
        sys.exit(EXIT_NO_DATA)

    df = pd.DataFrame(data)
    cols = ["rank", "ticker", "rsrs", "avg_vol_20d", "last_close"]
    if "pct_change_60d" in df.columns:
        cols.append("pct_change_60d")

    # rank(.0f), ticker(str), rsrs(.6f), avg_vol_20d(.0f), last_close(.2f), pct_change_60d(.2f)
    print(tabulate(df[cols], headers="keys", tablefmt="simple", showindex=False,
                   floatfmt=(".0f", ".6f", ".0f", ".2f", ".2f", ".2f")))


def cmd_breadth(args):
    """Query market breadth (advancers/decliners) via BreadthService."""
    data = build_breadth_service().breadth(args.market, args.days)

    if not data:
        print("no data")
        sys.exit(EXIT_NO_DATA)

    df = pd.DataFrame(data)
    print(tabulate(df, headers="keys", tablefmt="simple", showindex=False,
                   floatfmt=(".0f", ".0f", ".0f", ".2f", ".2f")))


def cmd_anomaly(args):
    """Query volume anomalies via AnomalyService."""
    data = build_anomaly_service().anomalies(args.min_ratio, args.top)

    if not data:
        print("no anomalies found")
        sys.exit(EXIT_NO_DATA)

    df = pd.DataFrame(data)
    print(tabulate(df, headers="keys", tablefmt="simple", showindex=False,
                   floatfmt=(".0f", ".2f", ".2f")))


def cmd_demo(args):
    """Zero-config demo walkthrough using bundled sample data.

    Runs RSRS ranking, market breadth, volume anomalies, and a sample stock
    query through the existing service seam. Requires no ``DEEPSEEK_API_KEY``.
    """
    market = args.market
    top = args.top
    sample_ticker = "600000.SH" if market == "cn" else "AAPL"

    print("=" * 60)
    print("MY-DOGE-MICRO 5-Minute Demo — using bundled sample data")
    print("=" * 60)

    ranking = build_ranking_service().rsrs(market, top)
    if ranking:
        print(f"\nTop {top} momentum stocks (RSRS) — {market.upper()}")
        df = pd.DataFrame(ranking)
        cols = ["rank", "ticker", "rsrs", "avg_vol_20d", "last_close"]
        if "pct_change_60d" in df.columns:
            cols.append("pct_change_60d")
        print(tabulate(df[cols], headers="keys", tablefmt="simple",
                       showindex=False, floatfmt=(".0f", ".6f", ".0f", ".2f", ".2f", ".2f")))
    else:
        print(f"\nNo RSRS data available for {market.upper()}")

    breadth = build_breadth_service().breadth(market, days=5)
    if breadth:
        print(f"\nLast 5 days market breadth — {market.upper()}")
        df = pd.DataFrame(breadth)
        print(tabulate(df, headers="keys", tablefmt="simple", showindex=False,
                       floatfmt=(".0f", ".0f", ".0f", ".2f", ".2f")))
    else:
        print(f"\nNo breadth data available for {market.upper()}")

    anomalies = build_anomaly_service().anomalies(min_ratio=3.0, top=top)
    if anomalies:
        print(f"\nTop {top} volume anomalies — CN")
        df = pd.DataFrame(anomalies)
        print(tabulate(df, headers="keys", tablefmt="simple", showindex=False,
                       floatfmt=(".0f", ".2f", ".2f")))
    else:
        print("\nNo volume anomalies available")

    stock = build_stock_service().query(sample_ticker, market, days=10)
    if stock:
        print(f"\nSample stock query — {sample_ticker}")
        df = pd.DataFrame(stock)
        print(tabulate(df, headers="keys", tablefmt="simple", showindex=False,
                       floatfmt=(".0f", ".2f", ".2f", ".2f", ".2f", ".0f")))
    else:
        print(f"\nNo data for sample ticker {sample_ticker}")

    has_any = ranking or breadth or anomalies or stock
    if not has_any:
        print(
            "\nNo demo data found. Make sure the bundled data files exist; see "
            "docs/GETTING_STARTED.md for data population instructions."
        )
        sys.exit(EXIT_NO_DATA)

    print("\nDemo complete. See docs/GETTING_STARTED.md for the full walkthrough.")
    print("For LLM-powered reports, set DEEPSEEK_API_KEY and run: python -m macro.cli")


def main():
    """Parse argv and dispatch to the matching command handler."""
    parser = argparse.ArgumentParser(
        prog="doge",
        description="MY-DOGE stock data query tool",
    )
    sub = parser.add_subparsers(dest="cmd")

    # stock
    p_stock = sub.add_parser("stock", help="query stock price and indicators")
    p_stock.add_argument("ticker", help="ticker symbol (e.g. 301599.SZ, AAPL)")
    p_stock.add_argument("--market", default="cn", choices=["cn", "us"])
    p_stock.add_argument("--days", type=int, default=20)

    # rsrs
    p_rsrs = sub.add_parser("rsrs", help="RSRS momentum ranking")
    p_rsrs.add_argument("--market", default="cn", choices=["cn", "us"])
    p_rsrs.add_argument("--top", type=int, default=20)

    # breadth
    p_breadth = sub.add_parser("breadth", help="market breadth (advancers/decliners)")
    p_breadth.add_argument("--market", default="cn", choices=["cn", "us"])
    p_breadth.add_argument("--days", type=int, default=10)

    # anomaly
    p_anomaly = sub.add_parser("anomaly", help="volume anomaly detection")
    p_anomaly.add_argument("--min-ratio", type=float, default=3.0)
    p_anomaly.add_argument("--top", type=int, default=20)

    # demo
    p_demo = sub.add_parser("demo", help="5-minute demo using bundled sample data")
    p_demo.add_argument("--market", default="cn", choices=["cn", "us"])
    p_demo.add_argument("--top", type=int, default=5)

    args = parser.parse_args()
    if args.cmd is None:
        parser.print_help()
        return

    dispatch = {
        "stock": cmd_stock,
        "rsrs": cmd_rsrs,
        "breadth": cmd_breadth,
        "anomaly": cmd_anomaly,
        "demo": cmd_demo,
    }
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
