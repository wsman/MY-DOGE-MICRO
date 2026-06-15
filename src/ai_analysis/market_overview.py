"""Deprecated market-overview module — forwards to ``GenerateMarketOverviewUseCase``.

``src/ai_analysis/market_overview.py`` is kept as a backwards-compatible shim
for Sprint 007. The canonical implementation now lives in
``doge.application.use_cases.generate_market_overview``. This module re-exports
``generate()`` so existing scripts and tests keep working. It will be removed in
Sprint 008.
"""
import warnings

warnings.warn(
    "ai_analysis.market_overview is deprecated; use "
    "doge.application.use_cases.generate_market_overview instead",
    DeprecationWarning,
    stacklevel=2,
)

from doge.application.composition import build_generate_market_overview_use_case
from doge.application.contracts.request import GenerateMarketOverviewRequest


def generate():
    """生成 Markdown 格式市场全景日报"""
    uc = build_generate_market_overview_use_case()
    resp = uc.execute(GenerateMarketOverviewRequest())
    return resp.markdown


if __name__ == "__main__":
    generate()
