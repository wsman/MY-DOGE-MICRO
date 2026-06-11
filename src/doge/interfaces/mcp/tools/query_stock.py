"""MCP tool: query_stock — delegates to StockService."""

import logging
import sqlite3

from doge.config import get_settings
from doge.core.services import StockService
from doge.infrastructure.database.repositories import DuckDBStockRepository
from doge.infrastructure.database.duckdb import DuckDBConnection
from doge.infrastructure.cache.ticker_cache import JSONTickerNameCache

logger = logging.getLogger(__name__)


def normalize_ticker(ticker: str, market: str = "cn") -> str:
    """Normalize bare code to exchange-suffixed ticker.

    Mirrors the legacy ``ai_analysis.normalize_ticker`` contract: rejects
    non-strings, empty input, codes longer than 20 chars, and codes containing
    characters outside ``[A-Za-z0-9.\\-]``. Codes already carrying an exchange
    suffix (``.``) and non-CN markets are returned unchanged.
    """
    import re
    if not isinstance(ticker, str):
        raise ValueError("ticker must be a string")
    code = ticker.strip()
    if not code:
        raise ValueError("ticker is required")
    if len(code) > 20:
        raise ValueError("ticker too long (max 20 chars)")
    if not re.match(r"^[A-Za-z0-9.\-]+$", code):
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


def _fmt(columns, rows):
    if not rows:
        return ""
    cw = [len(c) for c in columns]
    sr = []
    for row in rows:
        tr = []
        for i, v in enumerate(row):
            s = f"{v:.2f}" if isinstance(v, float) else str(v)
            tr.append(s)
            cw[i] = max(cw[i], len(s))
        sr.append(tr)
    lines = ["  ".join(c.ljust(cw[i]) for i, c in enumerate(columns))]
    for r in sr:
        lines.append("  ".join(s.ljust(cw[i]) for i, s in enumerate(r)))
    return "\n".join(lines)


async def query_stock(ticker: str, market: str = "cn", days: int = 20) -> str:
    """Query stock OHLCV + indicators."""
    t = normalize_ticker(ticker, market)
    repo = DuckDBStockRepository(DuckDBConnection(read_only=True))
    svc = StockService(repo)
    data = svc.query(t, market, days)
    if not data:
        return f"No data for {t}"
    return _fmt(list(data[0].keys()), [list(r.values()) for r in data])


async def stock_overview(ticker: str, market: str = "cn") -> str:
    """Stock overview: name, sector, latest price, notes.

    Parity-faithful with the legacy ``mcp_server.stock_overview``: emits name +
    sector (from the stock_names table), latest prices (via StockService), and a
    笔记 block read from stock_notes with dynamic ``deleted_at`` filtering so
    soft-deleted notes do not leak (CDD module #7 §3.3 / #8 fix). The clean
    NoteRepository port is module #7's own scope; this tool reads the notes table
    directly for output parity until that repository lands.
    """
    t = normalize_ticker(ticker, market)
    repo = DuckDBStockRepository(DuckDBConnection(read_only=True))
    svc = StockService(repo)
    overview = svc.overview(t, market)

    lines = [f"=== {t} ({market.upper()}) ==="]

    # 名称 + 板块 (stock_names table — JSONTickerNameCache only carries names,
    # so read sector directly for parity with the legacy tool).
    try:
        conn = sqlite3.connect(str(get_settings().db.research_db))
        cur = conn.cursor()
        row = cur.execute(
            "SELECT name_cn, sector FROM stock_names WHERE ticker=?", (t,)
        ).fetchone()
        if row:
            if row[0]:
                lines.append(f"名称: {row[0]}")
            if row[1]:
                lines.append(f"板块: {row[1]}")
        conn.close()
    except sqlite3.Error as exc:
        logger.error("stock_overview SQLite error (names): %s", exc, exc_info=True)

    prices = overview.get("prices", [])
    if prices:
        latest = prices[0]
        lines.append(f"\n最新: {latest['date']} 收盘: {latest['close']}")
        if len(prices) > 1:
            prev = prices[1]
            chg = (latest["close"] - prev["close"]) / prev["close"] * 100
            lines.append(f"涨跌幅: {chg:.2f}%")
        for p in prices:
            lines.append(f"  {p['date']} | O:{p['open']} H:{p['high']} L:{p['low']} C:{p['close']} V:{p['volume']}")

    # 笔记 (notes) — soft-delete-aware: detect the deleted_at column once and
    # filter it so soft-deleted notes do not leak into MCP responses.
    try:
        conn = sqlite3.connect(str(get_settings().db.research_db))
        cur = conn.cursor()
        has_deleted_at = "deleted_at" in {
            row[1] for row in cur.execute("PRAGMA table_info(stock_notes)").fetchall()
        }
        deleted_pred = " AND deleted_at IS NULL" if has_deleted_at else ""
        n = cur.execute(
            f"SELECT COUNT(*) FROM stock_notes WHERE ticker=?{deleted_pred}", (t,)
        ).fetchone()[0]
        notes = cur.execute(
            f"SELECT created_at, content FROM stock_notes WHERE ticker=?{deleted_pred} "
            f"ORDER BY created_at DESC LIMIT 5",
            (t,),
        ).fetchall()
        conn.close()
        if notes:
            lines.append(f"\n笔记 ({n} 条):")
            for x in notes:
                lines.append(f"  [{x[0]}] {x[1][:80]}")
        else:
            lines.append("\n暂无笔记")
    except sqlite3.Error as exc:
        logger.error("stock_overview SQLite error (notes): %s", exc, exc_info=True)
        lines.append("\n暂无笔记")

    return "\n".join(lines)
