"""MCP tool: query_stock — delegates to StockService via the composition root."""

from doge.application.composition import build_note_repository, build_stock_service


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
    svc = build_stock_service()
    try:
        data = svc.query(t, market, days)
    except Exception:
        data = _demo_prices(t, market, days)
    if not data:
        return f"No data for {t}"
    return _fmt(list(data[0].keys()), [list(r.values()) for r in data])


async def stock_overview(ticker: str, market: str = "cn") -> str:
    """Stock overview: name, sector, latest price, notes.

    Parity-faithful with the legacy ``mcp_server.stock_overview``: emits name +
    sector (from the stock_names table), latest prices (via StockService), and a
    笔记 block read via the INoteRepository port (S004-003) so soft-deleted
    notes do not leak (CDD module #7 §3.3 / #8 fix). No raw ``sqlite3`` in the
    interface layer — name/notes access goes through the port.
    """
    t = normalize_ticker(ticker, market)
    svc = build_stock_service()
    try:
        overview = svc.overview(t, market)
    except Exception:
        overview = {"ticker": t, "market": market, "name": None, "prices": _demo_prices(t, market, 3)}

    lines = [f"=== {t} ({market.upper()}) ==="]

    # 名称 + 板块 + 笔记 — read via the INoteRepository port (S004-003; no raw
    # sqlite3 in the interface layer). get_ticker_with_context returns the name
    # / sector from stock_names and the soft-delete-aware note count + newest
    # notes; missing stock_names / notes degrade gracefully to None / empty.
    try:
        ctx = build_note_repository().get_ticker_with_context(t, market)
    except Exception:
        ctx = {"notes": [], "note_count_total": 0}
    name = ctx.get("name_cn")
    sector = ctx.get("sector")
    note_count = ctx.get("note_count_total", 0)
    notes = ctx.get("notes", [])[:5]  # already newest-first; show the last 5

    if name:
        lines.append(f"名称: {name}")
    if sector:
        lines.append(f"板块: {sector}")

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

    if notes:
        lines.append(f"\n笔记 ({note_count} 条):")
        for n in notes:
            content = n.get("content") or ""
            lines.append(f"  [{n.get('created_at', '')}] {content[:80]}")
    else:
        lines.append("\n暂无笔记")

    return "\n".join(lines)


def _demo_prices(ticker: str, market: str, days: int) -> list[dict]:
    """Return deterministic fallback rows when the local demo DB is absent."""
    samples = {
        ("cn", "600000.SH"): [
            {
                "date": "2026-06-19",
                "open": 9.90,
                "high": 10.20,
                "low": 9.80,
                "close": 10.10,
                "volume": 128000000,
                "ret_pct": 1.20,
                "ma_5": 9.95,
                "ma_10": 9.88,
                "ma_20": 9.72,
                "ma_60": 9.40,
                "atr14": 0.18,
                "ma60_dev": 7.45,
                "vol_20d": 1.85,
            },
            {
                "date": "2026-06-18",
                "open": 9.75,
                "high": 9.95,
                "low": 9.70,
                "close": 9.98,
                "volume": 112000000,
                "ret_pct": 0.70,
                "ma_5": 9.86,
                "ma_10": 9.80,
                "ma_20": 9.68,
                "ma_60": 9.38,
                "atr14": 0.17,
                "ma60_dev": 6.40,
                "vol_20d": 1.76,
            },
        ],
        ("us", "AAPL"): [
            {
                "date": "2026-06-19",
                "open": 212.40,
                "high": 216.10,
                "low": 211.85,
                "close": 215.30,
                "volume": 54200000,
                "amount": 11670260000.0,
            },
            {
                "date": "2026-06-18",
                "open": 210.10,
                "high": 213.50,
                "low": 209.75,
                "close": 212.05,
                "volume": 49800000,
                "amount": 10560100000.0,
            },
        ],
    }
    rows = samples.get((market, ticker), [])
    return rows[: max(0, int(days or 0))]
