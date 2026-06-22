"""MCP tool: list_views."""

import json

from doge.application import composition


async def list_views() -> str:
    try:
        rows = composition.build_tool_application_service().list_views()["views"]
        if not rows:
            return json.dumps(_fallback_views(), indent=2, ensure_ascii=False)
        return json.dumps(rows, indent=2, ensure_ascii=False)
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
