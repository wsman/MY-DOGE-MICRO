"""MCP tool: volume_anomalies."""

from doge.application.agent.tool_service import ToolApplicationService


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


async def volume_anomalies(min_ratio: float = 3.0, top: int = 20) -> str:
    try:
        data = ToolApplicationService().volume_anomalies(min_ratio, top)["rows"]
    except Exception:
        data = []
    if not data:
        return "No anomalies"
    return _fmt(list(data[0].keys()), [list(r.values()) for r in data])
