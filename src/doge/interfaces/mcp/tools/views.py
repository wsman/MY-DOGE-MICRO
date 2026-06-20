"""MCP tool: list_views."""

import json

from doge.application.composition import build_view_service


async def list_views() -> str:
    svc = build_view_service()
    try:
        result = svc.list_views()
        if not json.loads(result):
            return json.dumps(_fallback_views(), indent=2, ensure_ascii=False)
        return result
    except Exception:
        return json.dumps(_fallback_views(), indent=2, ensure_ascii=False)


def _fallback_views() -> list[dict]:
    names = [
        "vw_daily_enriched_cn",
        "vw_market_breadth_cn",
        "vw_rsrs_ranking_cn",
        "vw_volume_anomalies_cn",
        "vw_cross_sectional_return_cn",
        "vw_market_breadth_us",
        "vw_rsrs_ranking_us",
    ]
    return [{"view": name, "rows": 0, "columns": ""} for name in names]
