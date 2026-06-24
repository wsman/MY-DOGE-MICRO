"""MCP tools: rsrs_ranking, market_breadth."""

from doge.bootstrap import build_gateway_container


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


async def rsrs_ranking(market: str = "cn", top: int = 20) -> str:
    try:
        data = build_ranking_service().rsrs(market, top)
    except Exception:
        data = []
    if not data:
        return "No data"
    return _fmt(list(data[0].keys()), [list(r.values()) for r in data])


async def market_breadth(market: str = "cn", days: int = 10) -> str:
    try:
        data = build_breadth_service().breadth(market, days)
    except Exception:
        data = []
    if not data:
        return "No data"
    return _fmt(list(data[0].keys()), [list(r.values()) for r in data])


def build_ranking_service():
    return build_gateway_container().build_ranking_service()


def build_breadth_service():
    return build_gateway_container().build_breadth_service()
