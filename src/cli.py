"""
MY-DOGE CLI — 股票数据查询工具

Usage:
    python src/cli.py stock <ticker> [--market cn] [--days 20]
    python src/cli.py rsrs [--market cn] [--top 20]
    python src/cli.py breadth [--market cn] [--days 10]
    python src/cli.py anomaly [--min-ratio 3.0] [--top 20]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_analysis import connect_duckdb, query_sql, normalize_ticker


def cmd_stock(args):
    con = connect_duckdb(read_only=True)
    market = args.market
    ticker = normalize_ticker(args.ticker, market)
    if market == "cn":
        sql = """
            SELECT date, open, high, low, close, volume,
                   ROUND(return_pct, 2) AS ret_pct,
                   ma_5, ma_10, ma_20, ma_60,
                   ROUND(atr_14, 2) AS atr14,
                   ROUND(ma60_deviation, 2) AS ma60_dev,
                   ROUND(volatility_20d, 2) AS vol_20d
            FROM vw_daily_enriched_cn
            WHERE ticker = ?
            ORDER BY date DESC
            LIMIT ?
        """
    else:
        sql = """
            SELECT date, open, high, low, close, volume, amount
            FROM us.stock_prices
            WHERE ticker = ?
            ORDER BY date DESC
            LIMIT ?
        """
    df = con.execute(sql, [ticker, args.days]).df()
    con.close()

    if df.empty:
        print(f"no data for {args.ticker}")
        return

    from tabulate import tabulate
    print(tabulate(df, headers="keys", tablefmt="simple", showindex=False,
                   floatfmt=(".0f", ".2f", ".2f", ".2f", ".2f", ".0f")))


def cmd_rsrs(args):
    con = connect_duckdb(read_only=True)
    view = "vw_rsrs_ranking_cn" if args.market == "cn" else "vw_rsrs_ranking_us"
    df = con.execute(f"SELECT * FROM {view} LIMIT ?", [args.top]).df()
    con.close()

    if df.empty:
        print("no data")
        return

    cols = ["rank", "ticker", "rsrs", "avg_vol_20d", "last_close"]
    if "pct_change_60d" in df.columns:
        cols.append("pct_change_60d")

    from tabulate import tabulate
    # rank(.0f), ticker(str), rsrs(.6f), avg_vol_20d(.0f), last_close(.2f), pct_change_60d(.2f)
    print(tabulate(df[cols], headers="keys", tablefmt="simple", showindex=False,
                   floatfmt=(".0f", ".6f", ".0f", ".2f", ".2f", ".2f")))


def cmd_breadth(args):
    con = connect_duckdb(read_only=True)
    view = "vw_market_breadth_cn" if args.market == "cn" else "vw_market_breadth_us"
    df = con.execute(f"SELECT * FROM {view} LIMIT ?", [args.days]).df()
    con.close()

    if df.empty:
        print("no data")
        return

    from tabulate import tabulate
    print(tabulate(df, headers="keys", tablefmt="simple", showindex=False,
                   floatfmt=(".0f", ".0f", ".0f", ".2f", ".2f")))


def cmd_anomaly(args):
    con = connect_duckdb(read_only=True)
    df = con.execute("""
        SELECT ticker, date, volume, ROUND(avg_vol_20d, 0) AS avg_vol,
               vol_ratio, ROUND(intraday_return, 2) AS ret_pct
        FROM vw_volume_anomalies_cn
        WHERE vol_ratio >= ?
        ORDER BY vol_ratio DESC
        LIMIT ?
    """, [args.min_ratio, args.top]).df()
    con.close()

    if df.empty:
        print("no anomalies found")
        return

    from tabulate import tabulate
    print(tabulate(df, headers="keys", tablefmt="simple", showindex=False,
                   floatfmt=(".0f", ".2f", ".2f")))


def main():
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

    args = parser.parse_args()
    if args.cmd is None:
        parser.print_help()
        return

    dispatch = {
        "stock": cmd_stock,
        "rsrs": cmd_rsrs,
        "breadth": cmd_breadth,
        "anomaly": cmd_anomaly,
    }
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
