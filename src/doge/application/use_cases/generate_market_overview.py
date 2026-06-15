"""Generate market overview report use case.

Generates a Markdown market-overview report from DuckDB analytical views.
Replaces ``src/ai_analysis/market_overview.py`` with a port-backed
implementation.
"""

from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

from doge.application.contracts.request import GenerateMarketOverviewRequest
from doge.application.contracts.response import MarketOverviewResponse
from doge.config import get_settings
from doge.core.ports.market_view import IMarketViewRepository
from doge.core.services.breadth_service import BreadthService
from doge.core.services.ranking_service import RankingService
from doge.core.services.anomaly_service import AnomalyService


class GenerateMarketOverviewUseCase:
    """Generate a Markdown market overview report."""

    def __init__(
        self,
        view_repo: IMarketViewRepository,
        breadth_service: BreadthService,
        ranking_service: RankingService,
        anomaly_service: AnomalyService,
    ) -> None:
        """Initialize with injected services.

        Args:
            view_repo: Read-only DuckDB view execution handle.
            breadth_service: Service for market-breadth queries.
            ranking_service: Service for RSRS ranking queries.
            anomaly_service: Service for volume-anomaly queries.
        """
        self._view_repo = view_repo
        self._breadth_service = breadth_service
        self._ranking_service = ranking_service
        self._anomaly_service = anomaly_service

    def execute(self, request: GenerateMarketOverviewRequest) -> MarketOverviewResponse:
        """Run the overview workflow and write a Markdown report."""
        now = datetime.now()
        today_str = now.strftime("%Y%m%d")
        date_label = now.strftime("%Y-%m-%d %H:%M")

        report_dir = get_settings().report_dir
        report_dir.mkdir(parents=True, exist_ok=True)
        out_path = report_dir / f"market_overview_{today_str}.md"

        # Latest date anchor
        max_d = self._max_date()
        if max_d is None:
            markdown = self._render_empty(date_label)
            out_path.write_text(markdown, encoding="utf-8")
            return MarketOverviewResponse(market=request.market, markdown=markdown)

        cutoff_10d = (max_d - timedelta(days=10)).strftime("%Y-%m-%d")
        cutoff_90d = (max_d - timedelta(days=90)).strftime("%Y-%m-%d")

        stats = self._market_stats(cutoff_10d)
        breadth = self._market_breadth(cutoff_90d)
        top20 = self._rsrs_top20(request.market, request.top)
        bottom20 = self._rsrs_bottom20(request.market, request.top)
        spikes = self._volume_spikes(request.market, request.top)

        markdown = self._render(
            date_label,
            max_d,
            stats,
            breadth,
            top20,
            bottom20,
            spikes,
        )
        out_path.write_text(markdown, encoding="utf-8")
        return MarketOverviewResponse(market=request.market, markdown=markdown)

    def _max_date(self) -> Optional[datetime]:
        df = self._view_repo.execute(
            "SELECT MAX(CAST(date AS DATE)) AS max_date FROM cn.stock_prices"
        )
        if df.empty or df["max_date"].iloc[0] is None:
            return None
        value = df["max_date"].iloc[0]
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value))

    def _market_stats(self, cutoff: str) -> pd.DataFrame:
        return self._view_repo.execute(
            """
            WITH daily_return AS (
                SELECT ticker, date, close,
                    LAG(close) OVER (PARTITION BY ticker ORDER BY date) AS prev_close
                FROM cn.stock_prices
                WHERE CAST(date AS DATE) >= ?
            ),
            classified AS (
                SELECT date,
                    CASE WHEN close > prev_close AND prev_close IS NOT NULL THEN 'up'
                         WHEN close < prev_close AND prev_close IS NOT NULL THEN 'down'
                         WHEN close = prev_close AND prev_close IS NOT NULL THEN 'flat' END AS direction,
                    ((close - prev_close) / NULLIF(prev_close, 0)) * 100 AS return_pct
                FROM daily_return
            )
            SELECT date,
                COUNT(*) FILTER (WHERE direction = 'up') AS advancers,
                COUNT(*) FILTER (WHERE direction = 'down') AS decliners,
                ROUND(AVG(return_pct) FILTER (WHERE direction IS NOT NULL), 4) AS avg_return_pct,
                ROUND(COUNT(*) FILTER (WHERE direction = 'up') * 100.0 /
                      NULLIF(COUNT(*) FILTER (WHERE direction IS NOT NULL), 0), 2) AS advance_ratio
            FROM classified GROUP BY date ORDER BY date DESC
            """,
            [cutoff],
        )

    def _market_breadth(self, cutoff: str) -> pd.DataFrame:
        return self._view_repo.execute(
            """
            WITH daily_return AS (
                SELECT ticker, date, close,
                    LAG(close) OVER (PARTITION BY ticker ORDER BY date) AS prev_close
                FROM cn.stock_prices
                WHERE CAST(date AS DATE) >= ?
            ),
            classified AS (
                SELECT date,
                    CASE WHEN close > prev_close AND prev_close IS NOT NULL THEN 'up'
                         WHEN close < prev_close AND prev_close IS NOT NULL THEN 'down'
                         WHEN close = prev_close AND prev_close IS NOT NULL THEN 'flat' END AS direction,
                    ((close - prev_close) / NULLIF(prev_close, 0)) * 100 AS return_pct
                FROM daily_return
            )
            SELECT date,
                COUNT(*) FILTER (WHERE direction = 'up') AS advancers,
                COUNT(*) FILTER (WHERE direction = 'down') AS decliners,
                COUNT(*) FILTER (WHERE direction = 'flat') AS unchanged,
                COUNT(*) FILTER (WHERE direction IS NOT NULL) AS active,
                ROUND(AVG(return_pct) FILTER (WHERE direction IS NOT NULL), 4) AS avg_return_pct,
                ROUND(STDDEV_POP(return_pct) FILTER (WHERE direction IS NOT NULL), 4) AS std_return_pct,
                ROUND(COUNT(*) FILTER (WHERE direction = 'up') * 100.0 /
                      NULLIF(COUNT(*) FILTER (WHERE direction IS NOT NULL), 0), 2) AS advance_ratio
            FROM classified GROUP BY date ORDER BY date DESC
            """,
            [cutoff],
        )

    def _rsrs_top20(self, market: str, top: int) -> pd.DataFrame:
        view = f"vw_rsrs_ranking_{market}"
        return self._view_repo.execute(
            f"""
            SELECT rank, ticker, rsrs, last_close, pct_change_60d, avg_vol_20d
            FROM {view}
            WHERE rank <= ?
            ORDER BY rank
            """,
            [top],
        )

    def _rsrs_bottom20(self, market: str, top: int) -> pd.DataFrame:
        view = f"vw_rsrs_ranking_{market}"
        return self._view_repo.execute(
            f"""
            SELECT rank, ticker, rsrs, last_close, pct_change_60d, avg_vol_20d
            FROM {view}
            ORDER BY rank DESC
            LIMIT ?
            """,
            [top],
        )

    def _volume_spikes(self, market: str, top: int) -> pd.DataFrame:
        # Reuse the anomaly service but cap at 15 for the overview report.
        rows = self._anomaly_service.anomalies(min_ratio=2.0, top=15)
        return pd.DataFrame(rows)

    def _render(
        self,
        date_label: str,
        max_d: datetime,
        stats: pd.DataFrame,
        breadth: pd.DataFrame,
        top20: pd.DataFrame,
        bottom20: pd.DataFrame,
        spikes: pd.DataFrame,
    ) -> str:
        lines = ["# 市场全景报告\n", f"> 生成时间: {date_label} | 数据截止: {max_d}\n"]

        lines.append("## 1. 最近交易日统计\n")
        if not stats.empty:
            lines.append(stats.to_markdown(index=False))
        else:
            lines.append("_无近期数据_")
        lines.append("\n")

        lines.append("## 2. 市场宽度 (近 90 日)\n")
        if not breadth.empty:
            lines.append(breadth.to_markdown(index=False))
        else:
            lines.append("_无近期数据_")
        lines.append("\n")

        lines.append("## 3. RSRS 动量 Top 20 (最强趋势)\n")
        if not top20.empty:
            lines.append(top20.to_markdown(index=False))
        else:
            lines.append("_无数据_")
        lines.append("\n")

        lines.append("## 4. RSRS 动量 Bottom 20 (最弱趋势)\n")
        if not bottom20.empty:
            lines.append(bottom20.to_markdown(index=False))
        else:
            lines.append("_无数据_")
        lines.append("\n")

        lines.append("## 5. 成交量异常 (放量 >2 倍, Top 15)\n")
        if not spikes.empty:
            lines.append(spikes.to_markdown(index=False))
        else:
            lines.append("_无符合条件的结果_")
        lines.append("\n")

        return "\n".join(lines)

    def _render_empty(self, date_label: str) -> str:
        return (
            f"# 市场全景报告\n\n"
            f"> 生成时间: {date_label} | 数据截止: _无数据_\n\n"
            "_无近期数据_\n"
        )
