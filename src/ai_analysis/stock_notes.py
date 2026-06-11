"""
股票评论系统 — 永久存档 + DuckDB 股价联合查询

- stock_notes 表存储在 research_insights.db (SQLite)，永久保留
- 股价数据来自 DuckDB -> market_data_cn/us.db，仅保留近半年
"""

import os
import sys
import sqlite3
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_analysis import connect_duckdb, get_project_path

NOTES_DB = get_project_path("data", "research_insights.db")


def _notes_conn():
    return sqlite3.connect(NOTES_DB)


def add_note(ticker, content, market="cn", note_type="comment",
             title=None, tags=None, price_at_note=None):
    """添加一条评论"""
    conn = _notes_conn()
    cur = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
        INSERT INTO stock_notes (ticker, market, created_at, note_type, title, content, tags, price_at_note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (ticker, market, now, note_type, title, content, tags, price_at_note))
    conn.commit()
    note_id = cur.lastrowid
    conn.close()
    return note_id


def get_notes(ticker, limit=None, days_back=None, note_type=None):
    """查询某标的的评论"""
    conn = _notes_conn()
    cur = conn.cursor()
    sql = "SELECT * FROM stock_notes WHERE ticker = ?"
    params = [ticker]
    if note_type:
        sql += " AND note_type = ?"
        params.append(note_type)
    if days_back:
        from datetime import datetime, timedelta
        cutoff = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        sql += " AND created_at >= ?"
        params.append(cutoff)
    sql += " ORDER BY created_at DESC"
    if limit:
        sql += " LIMIT ?"
        params.append(limit)
    cur.execute(sql, params)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]


def get_ticker_with_context(ticker, market="cn", notes_limit=20):
    """联合查询：股价 (DuckDB 半年) + 评论 (SQLite 全量)"""
    result = {
        "ticker": ticker,
        "market": market,
        "name_cn": None,
        "name_en": None,
        "sector": None,
        "industry": None,
        "price_data": None,
        "notes": [],
        "note_count_total": 0,
    }

    # 0. 名称信息 (SQLite)
    try:
        conn = _notes_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT name_cn, name_en, sector, industry FROM stock_names WHERE ticker = ?",
            (ticker,)
        )
        row = cur.fetchone()
        if row:
            result["name_cn"] = row[0]
            result["name_en"] = row[1]
            result["sector"] = row[2]
            result["industry"] = row[3]
        conn.close()
    except Exception:
        pass

    # 1. 股价数据 (DuckDB, 近半年)
    try:
        con = connect_duckdb()
        db_label = "cn" if market == "cn" else "us"
        con.execute(
            "ATTACH IF NOT EXISTS '{}' AS {} (TYPE sqlite)".format(
                get_project_path("data", "market_data_{}.db".format(db_label)).replace("\\", "/"),
                db_label
            )
        )
        price_df = con.execute("""
            SELECT date, open, high, low, close, volume, amount
            FROM {}.stock_prices
            WHERE ticker = ?
            ORDER BY date DESC
        """.format(db_label), [ticker]).df()
        con.close()
        if not price_df.empty:
            result["price_data"] = price_df.to_dict(orient="records")
    except Exception as e:
        result["price_error"] = str(e)

    # 2. 评论数据 (SQLite, 全量)
    try:
        conn = _notes_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM stock_notes WHERE ticker = ?", (ticker,)
        )
        result["note_count_total"] = cur.fetchone()[0]
        cur.execute(
            """SELECT id, created_at, note_type, title, content, tags, price_at_note, source
               FROM stock_notes WHERE ticker = ?
               ORDER BY created_at DESC LIMIT ?""",
            (ticker, notes_limit)
        )
        cols = [d[0] for d in cur.description]
        result["notes"] = [dict(zip(cols, r)) for r in cur.fetchall()]
        conn.close()
    except Exception as e:
        result["notes_error"] = str(e)

    return result


def search_notes(keyword, limit=50):
    """全文搜索评论内容"""
    conn = _notes_conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT ticker, created_at, note_type, title, content
           FROM stock_notes WHERE content LIKE ? OR title LIKE ?
           ORDER BY created_at DESC LIMIT ?""",
        ("%{}%".format(keyword), "%{}%".format(keyword), limit)
    )
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()
    return rows


def list_tracked_tickers():
    """列出所有有评论记录的标的"""
    conn = _notes_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT ticker, market, COUNT(*) AS n, MAX(created_at) AS last_note "
        "FROM stock_notes GROUP BY ticker ORDER BY last_note DESC"
    )
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()
    return rows


def get_recent_notes(days=7, limit=100):
    """获取最近 N 天的所有评论"""
    conn = _notes_conn()
    cur = conn.cursor()
    from datetime import datetime, timedelta
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    cur.execute(
        """SELECT ticker, market, created_at, note_type, title, content, tags
           FROM stock_notes WHERE created_at >= ?
           ORDER BY created_at DESC LIMIT ?""",
        (cutoff, limit)
    )
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()
    return rows


# CLI
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="股票评论管理")
    sub = parser.add_subparsers(dest="cmd")

    add_p = sub.add_parser("add")
    add_p.add_argument("ticker")
    add_p.add_argument("content")
    add_p.add_argument("--title")
    add_p.add_argument("--tags")
    add_p.add_argument("--market", default="cn")

    query_p = sub.add_parser("query")
    query_p.add_argument("ticker")
    query_p.add_argument("--notes-limit", type=int, default=20)
    query_p.add_argument("--market", default="cn")

    list_p = sub.add_parser("list")
    search_p = sub.add_parser("search")
    search_p.add_argument("keyword")

    recent_p = sub.add_parser("recent")
    recent_p.add_argument("--days", type=int, default=7)

    args = parser.parse_args()

    if args.cmd == "add":
        nid = add_note(args.ticker, args.content, args.market,
                       title=args.title, tags=args.tags)
        print("note #{} added for {}".format(nid, args.ticker))
    elif args.cmd == "query":
        ctx = get_ticker_with_context(args.ticker, args.market, args.notes_limit)
        if ctx["price_data"]:
            print("=== Price ({} rows) ===".format(len(ctx["price_data"])))
            for r in ctx["price_data"][:5]:
                print("  {} | close={}".format(r["date"], r["close"]))
        print("=== Notes ({} total, showing {}) ===".format(
            ctx["note_count_total"], len(ctx["notes"])))
        for n in ctx["notes"]:
            print("  [{}] {}".format(n["created_at"], n["content"][:80]))
    elif args.cmd == "list":
        for r in list_tracked_tickers():
            print("  {} ({}) — {} notes, last: {}".format(
                r["ticker"], r["market"], r["n"], r["last_note"]))
    elif args.cmd == "search":
        for r in search_notes(args.keyword):
            print("  [{}] {}: {}".format(r["created_at"], r["ticker"], r["content"][:80]))
    elif args.cmd == "recent":
        for r in get_recent_notes(args.days):
            print("  [{}] {}: {}".format(r["created_at"], r["ticker"],
                                         (r["content"] or "")[:80]))
