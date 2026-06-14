"""MCP tools: rsrs_ranking, market_breadth."""

from doge.application.composition import build_breadth_service, build_ranking_service


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
    svc = build_ranking_service()
    data = svc.rsrs(market, top)
    if not data:
        return "No data"
    return _fmt(list(data[0].keys()), [list(r.values()) for r in data])


async def market_breadth(market: str = "cn", days: int = 10) -> str:
    svc = build_breadth_service()
    data = svc.breadth(market, days)
    if not data:
        return "No data"
    return _fmt(list(data[0].keys()), [list(r.values()) for r in data])
