"""Deprecated stock-notes module — forwards to ``ManageNotesUseCase``.

``src/ai_analysis/stock_notes.py`` is kept as a backwards-compatible shim for
Sprint 007. The canonical note operations now live in
``doge.application.use_cases.manage_notes``. This module re-exports the legacy
free functions so existing scripts and tests keep working. It will be removed in
Sprint 008.
"""
import warnings
from typing import Optional

warnings.warn(
    "ai_analysis.stock_notes is deprecated; use doge.application.use_cases.manage_notes instead",
    DeprecationWarning,
    stacklevel=2,
)

from doge.application.composition import build_manage_notes_use_case
from doge.application.contracts.request import ManageNoteRequest


# Compatibility constant — no longer read internally, but preserved so callers
# that monkeypatch it are not surprised. New code should use ``DOGE_RESEARCH_DB``.
NOTES_DB = None


_NOTES_DB = None


def _uc():
    return build_manage_notes_use_case()


def add_note(ticker, content, market="cn", note_type="comment",
             title=None, tags=None, price_at_note=None):
    """添加一条评论"""
    resp = _uc().execute(
        ManageNoteRequest(
            operation="add",
            ticker=ticker,
            note_text=content,
            market=market,
            note_type=note_type,
            title=title,
            tags=tags,
            price_at_note=price_at_note,
        )
    )
    return resp.note_id


def get_notes(ticker, limit=None, days_back=None, note_type=None):
    """查询某标的的评论 (soft-deleted rows excluded)."""
    resp = _uc().execute(
        ManageNoteRequest(
            operation="get_notes",
            ticker=ticker,
            limit=limit,
            days=days_back,
            note_type=note_type,
        )
    )
    return resp.notes


def get_ticker_with_context(ticker, market="cn", notes_limit=20):
    """联合查询：股价 (DuckDB 半年) + 评论 (SQLite 全量)"""
    resp = _uc().execute(
        ManageNoteRequest(
            operation="get_context",
            ticker=ticker,
            market=market,
            limit=notes_limit,
        )
    )
    return resp.context


def delete_note(note_id):
    """Soft-delete a note by id."""
    resp = _uc().execute(
        ManageNoteRequest(operation="delete", note_id=note_id)
    )
    return resp.success


def search_notes(keyword, limit=50):
    """全文搜索评论内容 (soft-deleted rows excluded)."""
    resp = _uc().execute(
        ManageNoteRequest(operation="search", keyword=keyword, limit=limit)
    )
    return resp.notes


def list_tracked_tickers():
    """列出所有有评论记录的标的 (soft-deleted notes excluded from counts)."""
    resp = _uc().execute(ManageNoteRequest(operation="tracked"))
    return resp.notes


def get_recent_notes(days=7, limit=100):
    """获取最近 N 天的所有评论 (soft-deleted rows excluded)."""
    resp = _uc().execute(
        ManageNoteRequest(operation="recent", days=days, limit=limit)
    )
    return resp.notes


# CLI shim
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
        if ctx.get("price_data"):
            print("=== Price ({} rows) ===".format(len(ctx["price_data"])))
            for r in ctx["price_data"][:5]:
                print("  {} | close={}".format(r["date"], r["close"]))
        print("=== Notes ({} total, showing {}) ===".format(
            ctx.get("note_count_total", 0), len(ctx.get("notes", []))))
        for n in ctx.get("notes", []):
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
