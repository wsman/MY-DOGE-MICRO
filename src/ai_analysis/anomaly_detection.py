"""
异常检测 —— 成交量异动、价格跳空、连续下跌/上涨

Usage:
    python src/ai_analysis/anomaly_detection.py [--days 3] [--min-ratio 3.0]
"""

import os
import argparse
from datetime import datetime, timedelta

# S002-009 / TR-011: package-qualified sibling import (editable install), no
# sys.path shim (ADR-0001 forbidden pattern ``sys_path_insert``).
from ai_analysis import (
    connect_duckdb,
    run_views_sql,
    ensure_report_dir,
    REPORT_DIR,
)


def volume_anomalies(con, min_ratio=3.0, cutoff=None):
    """成交量异常 (当日成交量 > N 倍 20 日均量)"""
    filter_clause = ""
    params = [min_ratio]
    if cutoff:
        filter_clause = " AND CAST(date AS DATE) >= ?"
        params.append(cutoff)
    return con.execute("""
        SELECT ticker, date, volume, avg_vol_20d, vol_ratio, intraday_return
        FROM vw_volume_anomalies_cn
        WHERE vol_ratio >= ?
        {}
        ORDER BY vol_ratio DESC
        LIMIT 30
    """.format(filter_clause), params).df()


def price_gaps(con, gap_threshold=5.0, cutoff=None):
    """价格跳空检测 (开盘价相对前日收盘价跳空 N%)"""
    return con.execute("""
        WITH gaps AS (
            SELECT ticker, date, open,
                LAG(close) OVER (PARTITION BY ticker ORDER BY date) AS prev_close,
                close
            FROM cn.stock_prices
            WHERE CAST(date AS DATE) >= ?
        ),
        gap_pct AS (
            SELECT ticker, date, open, prev_close, close,
                ROUND(((open - prev_close) / NULLIF(prev_close, 0)) * 100, 2) AS gap_pct,
                ROUND(((close - prev_close) / NULLIF(prev_close, 0)) * 100, 2) AS return_pct
            FROM gaps WHERE prev_close IS NOT NULL
        )
        SELECT * FROM gap_pct
        WHERE ABS(gap_pct) >= ?
        ORDER BY date DESC, ABS(gap_pct) DESC
        LIMIT 30
    """, [cutoff, gap_threshold]).df()


def consecutive_extremes(con, direction="down", min_days=5, cutoff=None):
    """连续涨/跌检测"""
    sign = "<" if direction == "down" else ">"
    return con.execute("""
        WITH returns AS (
            SELECT ticker, date, close,
                LAG(close) OVER (PARTITION BY ticker ORDER BY date) AS prev_close
            FROM cn.stock_prices
            WHERE CAST(date AS DATE) >= ?
        ),
        daily AS (
            SELECT ticker, date,
                CASE WHEN close {} prev_close THEN 1 ELSE 0 END AS streak_bit
            FROM returns WHERE prev_close IS NOT NULL
        ),
        streaks AS (
            SELECT ticker, date, streak_bit,
                SUM(CASE WHEN streak_bit = 0 THEN 1 ELSE 0 END)
                    OVER (PARTITION BY ticker ORDER BY date
                          ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS reset_group
            FROM daily
        ),
        grouped AS (
            SELECT ticker,
                MIN(date) AS from_date,
                MAX(date) AS to_date,
                COUNT(*) AS streak_days
            FROM streaks WHERE streak_bit = 1
            GROUP BY ticker, reset_group
            HAVING COUNT(*) >= ?
        )
        SELECT *
        FROM grouped
        WHERE CAST((SELECT MAX(date) FROM cn.stock_prices) AS DATE) - CAST(to_date AS DATE) <= 2
        ORDER BY streak_days DESC
        LIMIT 30
    """.format(sign), [cutoff, min_days]).df()


def generate(min_ratio=3.0, gap_threshold=5.0, recent_days=3):
    now = datetime.now()
    today_str = now.strftime("%Y%m%d")
    date_label = now.strftime("%Y-%m-%d %H:%M")

    ensure_report_dir()
    con = connect_duckdb()
    run_views_sql(con)

    max_d = con.execute(
        "SELECT MAX(CAST(date AS DATE)) FROM cn.stock_prices"
    ).fetchone()[0]
    cutoff = (max_d - timedelta(days=max(30, recent_days + 5))).strftime("%Y-%m-%d")

    vol_anom = volume_anomalies(con, min_ratio, cutoff)
    gaps = price_gaps(con, gap_threshold, cutoff)
    down_streaks = consecutive_extremes(con, "down", 5, cutoff)
    up_streaks = consecutive_extremes(con, "up", 5, cutoff)
    con.close()

    out_path = os.path.join(REPORT_DIR, "anomaly_detection_{}.md".format(today_str))

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# 异常检测报告\n\n")
        f.write("> 生成时间: {} | 数据截止: {} | 量比阈值: {}x | 跳空阈值: {}%\n\n".format(
            date_label, max_d, min_ratio, gap_threshold))

        f.write("## 1. 成交量异常 (量比 >= {}x)\n\n".format(min_ratio))
        if len(vol_anom) > 0:
            f.write(vol_anom.to_markdown(index=False))
        else:
            f.write("_无符合条件的结果_\n")
        f.write("\n\n")

        f.write("## 2. 跳空缺口 (|跳空| >= {}%)\n\n".format(gap_threshold))
        if len(gaps) > 0:
            f.write(gaps.to_markdown(index=False))
        else:
            f.write("_无符合条件的结果_\n")
        f.write("\n\n")

        f.write("## 3. 连续下跌 >= 5 天 (仍在持续)\n\n")
        if len(down_streaks) > 0:
            f.write(down_streaks.to_markdown(index=False))
        else:
            f.write("_无符合条件的结果_\n")
        f.write("\n\n")

        f.write("## 4. 连续上涨 >= 5 天 (仍在持续)\n\n")
        if len(up_streaks) > 0:
            f.write(up_streaks.to_markdown(index=False))
        else:
            f.write("_无符合条件的结果_\n")
        f.write("\n")

    print("report written → {}".format(out_path))
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="异常检测")
    parser.add_argument("--min-ratio", type=float, default=3.0, help="量比阈值 (default: 3.0)")
    parser.add_argument("--gap-threshold", type=float, default=5.0, help="跳空百分比阈值")
    parser.add_argument("--days", type=int, default=3, help="最近 N 天 (default: 3)")
    args = parser.parse_args()
    generate(args.min_ratio, args.gap_threshold, args.days)
