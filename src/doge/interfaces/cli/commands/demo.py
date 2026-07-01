"""CLI command: demo."""

import sys

from tabulate import tabulate

from doge.bootstrap import build_gateway_container
from doge.interfaces.cli.constants import DEMO_MACRO_HINT, EXIT_NO_DATA
from doge.interfaces.cli.formatters import fmt_anomaly_table, fmt_breadth_table, fmt_rsrs_table


def cmd_demo(args) -> None:
    """Zero-config demo walkthrough using bundled sample data."""
    market = args.market
    top = args.top
    sample_ticker = "600000.SH" if market == "cn" else "AAPL"

    print("=" * 60)
    print("MY-DOGE-MICRO 5-Minute Demo — using bundled sample data")
    print("=" * 60)

    ranking = build_ranking_service().rsrs(market, top)
    if ranking:
        print(f"\nTop {top} momentum stocks (RSRS) — {market.upper()}")
        print(fmt_rsrs_table(ranking))
    else:
        print(f"\nNo RSRS data available for {market.upper()}")

    breadth = build_breadth_service().breadth(market, days=5)
    if breadth:
        print(f"\nLast 5 days market breadth — {market.upper()}")
        print(fmt_breadth_table(breadth))
    else:
        print(f"\nNo breadth data available for {market.upper()}")

    anomalies = build_anomaly_service().anomalies(min_ratio=3.0, top=top)
    if anomalies:
        print(f"\nTop {top} volume anomalies — CN")
        print(fmt_anomaly_table(anomalies))
    else:
        print("\nNo volume anomalies available")

    stock = build_stock_service().query(sample_ticker, market, days=10)
    if stock:
        print(f"\nSample stock query — {sample_ticker}")
        df = __import__("pandas").DataFrame(stock)
        print(tabulate(df, headers="keys", tablefmt="simple", showindex=False,
                       floatfmt=(".0f", ".2f", ".2f", ".2f", ".2f", ".0f")))
    else:
        print(f"\nNo data for sample ticker {sample_ticker}")

    has_any = ranking or breadth or anomalies or stock
    if not has_any:
        print(
            "\nNo demo data found. Make sure the bundled data files exist; see "
            "docs/guides/getting-started.md for data population instructions."
        )
        sys.exit(EXIT_NO_DATA)

    print("\nDemo complete. See docs/guides/getting-started.md for the full walkthrough.")
    print(DEMO_MACRO_HINT)


def _gateway_container():
    return build_gateway_container()


def build_ranking_service():
    return _gateway_container().build_ranking_service()


def build_breadth_service():
    return _gateway_container().build_breadth_service()


def build_anomaly_service():
    return _gateway_container().build_anomaly_service()


def build_stock_service():
    return _gateway_container().build_stock_service()
