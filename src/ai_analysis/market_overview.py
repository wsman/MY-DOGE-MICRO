"""
市场全景分析 —— 生成 Markdown 格式日报

Usage:
    python src/ai_analysis/market_overview.py

Output:
    ai_report/market_overview_YYYYMMDD.md
"""

import os
from datetime import datetime

# S002-009 / TR-011: package-qualified sibling import (editable install), no
# sys.path shim (ADR-0001 forbidden pattern ``sys_path_insert``).
from ai_analysis import (
    connect_duckdb,
    run_views_sql,
    ensure_report_dir,
    REPORT_DIR,
)

# 以数据实际最大日期为锚点，而非系统 CURRENT_DATE
MAX_DATE_CTE = """
    max_d AS (SELECT MAX(CAST(date AS DATE)) AS max_date FROM cn.stock_prices)
"""


def market_breadth(con, cutoff):
    return con.execute("""
        WITH daily_return AS (
            SELECT ticker, date, close,
                LAG(close) OVER (PARTITION BY ticker ORDER BY date) AS prev_close
            FROM cn.stock_prices
            WHERE CAST(date AS DATE) >= ?
        ),
        classified AS (
            SELECT date,
                CASE WHEN close > prev_close AND prev_close IS NOT NULL THEN 'up'
                     WHEN close < prev_close AND prev_close IS NOT NULL THEN 'down'
                     WHEN close = prev_close AND prev_close IS NOT NULL THEN 'flat' END AS direction,
                ((close - prev_close) / NULLIF(prev_close, 0)) * 100 AS return_pct
            FROM daily_return
        )
        SELECT date,
            COUNT(*) FILTER (WHERE direction = 'up') AS advancers,
            COUNT(*) FILTER (WHERE direction = 'down') AS decliners,
            COUNT(*) FILTER (WHERE direction = 'flat') AS unchanged,
            COUNT(*) FILTER (WHERE direction IS NOT NULL) AS active,
            ROUND(AVG(return_pct) FILTER (WHERE direction IS NOT NULL), 4) AS avg_return_pct,
            ROUND(STDDEV_POP(return_pct) FILTER (WHERE direction IS NOT NULL), 4) AS std_return_pct,
            ROUND(COUNT(*) FILTER (WHERE direction = 'up') * 100.0 /
                  NULLIF(COUNT(*) FILTER (WHERE direction IS NOT NULL), 0), 2) AS advance_ratio
        FROM classified GROUP BY date ORDER BY date DESC
    """, [cutoff]).df()


def rsrs_top20(con):
    return con.execute("""
        SELECT rank, ticker, rsrs, last_close, pct_change_60d, avg_vol_20d
        FROM vw_rsrs_ranking_cn
        WHERE rank <= 20
        ORDER BY rank
    """).df()


def rsrs_bottom20(con):
    return con.execute("""
        SELECT rank, ticker, rsrs, last_close, pct_change_60d, avg_vol_20d
        FROM vw_rsrs_ranking_cn
        ORDER BY rank DESC
        LIMIT 20
    """).df()


def volume_spikes(con):
    return con.execute("""
        SELECT ticker, date, volume, avg_vol_20d, vol_ratio, intraday_return
        FROM vw_volume_anomalies_cn
        ORDER BY vol_ratio DESC
        LIMIT 15
    """).df()


def market_stats(con, cutoff):
    return con.execute("""
        WITH daily_return AS (
            SELECT ticker, date, close,
                LAG(close) OVER (PARTITION BY ticker ORDER BY date) AS prev_close
            FROM cn.stock_prices
            WHERE CAST(date AS DATE) >= ?
        ),
        classified AS (
            SELECT date,
                CASE WHEN close > prev_close AND prev_close IS NOT NULL THEN 'up'
                     WHEN close < prev_close AND prev_close IS NOT NULL THEN 'down'
                     WHEN close = prev_close AND prev_close IS NOT NULL THEN 'flat' END AS direction,
                ((close - prev_close) / NULLIF(prev_close, 0)) * 100 AS return_pct
            FROM daily_return
        )
        SELECT date,
            COUNT(*) FILTER (WHERE direction = 'up') AS advancers,
            COUNT(*) FILTER (WHERE direction = 'down') AS decliners,
            ROUND(AVG(return_pct) FILTER (WHERE direction IS NOT NULL), 4) AS avg_return_pct,
            ROUND(COUNT(*) FILTER (WHERE direction = 'up') * 100.0 /
                  NULLIF(COUNT(*) FILTER (WHERE direction IS NOT NULL), 0), 2) AS advance_ratio
        FROM classified GROUP BY date ORDER BY date DESC
    """, [cutoff]).df()


def generate():
    now = datetime.now()
    today_str = now.strftime("%Y%m%d")
    date_label = now.strftime("%Y-%m-%d %H:%M")

    ensure_report_dir()
    con = connect_duckdb()
    run_views_sql(con)

    # 获取数据实际最新日期
    max_d = con.execute(
        "SELECT MAX(CAST(date AS DATE)) FROM cn.stock_prices"
    ).fetchone()[0]

    import datetime as dt
    cutoff_10d = (max_d - dt.timedelta(days=10)).strftime("%Y-%m-%d")
    cutoff_90d = (max_d - dt.timedelta(days=90)).strftime("%Y-%m-%d")

    stats = market_stats(con, cutoff_10d)
    breadth = market_breadth(con, cutoff_90d)
    top20 = rsrs_top20(con)
    bottom20 = rsrs_bottom20(con)
    spikes = volume_spikes(con)
    con.close()

    out_path = os.path.join(REPORT_DIR, "market_overview_{}.md".format(today_str))

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# 市场全景报告\n\n")
        f.write("> 生成时间: {} | 数据截止: {}\n\n".format(date_label, max_d))

        f.write("## 1. 最近交易日统计\n\n")
        if len(stats) > 0:
            f.write(stats.to_markdown(index=False))
        else:
            f.write("_无近期数据_\n")
        f.write("\n\n")

        f.write("## 2. 市场宽度 (近 90 日)\n\n")
        if len(breadth) > 0:
            f.write(breadth.to_markdown(index=False))
        else:
            f.write("_无近期数据_\n")
        f.write("\n\n")

        f.write("## 3. RSRS 动量 Top 20 (最强趋势)\n\n")
        if len(top20) > 0:
            f.write(top20.to_markdown(index=False))
        else:
            f.write("_无数据_\n")
        f.write("\n\n")

        f.write("## 4. RSRS 动量 Bottom 20 (最弱趋势)\n\n")
        if len(bottom20) > 0:
            f.write(bottom20.to_markdown(index=False))
        else:
            f.write("_无数据_\n")
        f.write("\n\n")

        f.write("## 5. 成交量异常 (放量 >2 倍, Top 15)\n\n")
        if len(spikes) > 0:
            f.write(spikes.to_markdown(index=False))
        else:
            f.write("_无符合条件的结果_\n")
        f.write("\n")

    print("report written → {}".format(out_path))
    return out_path


if __name__ == "__main__":
    generate()
