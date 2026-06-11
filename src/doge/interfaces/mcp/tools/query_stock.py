"""MCP tool: query_stock — delegates to StockService."""

from doge.core.services import StockService
from doge.infrastructure.database.repositories import DuckDBStockRepository
from doge.infrastructure.database.duckdb import DuckDBConnection
from doge.infrastructure.cache.ticker_cache import JSONTickerNameCache


def normalize_ticker(ticker: str, market: str = "cn") -> str:
    """Normalize bare code to exchange-suffixed ticker."""
    import re
    code = ticker.strip()
    if not code:
        raise ValueError("ticker is required")
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
    """Stock overview: name, sector, latest price, notes."""
    t = normalize_ticker(ticker, market)
    repo = DuckDBStockRepository(DuckDBConnection(read_only=True))
    svc = StockService(repo)
    overview = svc.overview(t, market)

    lines = [f"=== {t} ({market.upper()}) ==="]
    cache = JSONTickerNameCache()
    name = cache.get(t)
    if name:
        lines.append(f"名称: {name}")

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

    return "\n".join(lines)
