"""Generate anomaly report use case.

Generates a Markdown anomaly-detection report from DuckDB analytical views.
Replaces ``src/ai_analysis/anomaly_detection.py`` with a port-backed
implementation.
"""

from datetime import datetime, timedelta

import pandas as pd

from doge.application.contracts.request import GenerateAnomalyReportRequest
from doge.application.contracts.response import AnomalyReportResponse
from doge.config import get_settings
from doge.core.ports.market_view import IMarketViewRepository
from doge.core.services.anomaly_service import AnomalyService


class GenerateAnomalyReportUseCase:
    """Generate a Markdown anomaly report."""

    def __init__(
        self,
        view_repo: IMarketViewRepository,
        anomaly_service: AnomalyService,
    ) -> None:
        """Initialize with injected services.

        Args:
            view_repo: Read-only DuckDB view execution handle.
            anomaly_service: Service for volume-anomaly queries.
        """
        self._view_repo = view_repo
        self._anomaly_service = anomaly_service

    def execute(self, request: GenerateAnomalyReportRequest) -> AnomalyReportResponse:
        """Run the anomaly report workflow."""
        now = datetime.now()
        today_str = now.strftime("%Y%m%d")
        date_label = now.strftime("%Y-%m-%d %H:%M")

        report_dir = get_settings().report_dir
        report_dir.mkdir(parents=True, exist_ok=True)
        out_path = report_dir / f"anomaly_detection_{today_str}.md"

        max_d = self._max_date()
        if max_d is None:
            markdown = self._render_empty(date_label, request)
            out_path.write_text(markdown, encoding="utf-8")
            return AnomalyReportResponse(market=request.market, markdown=markdown)

        cutoff = (max_d - timedelta(days=max(30, request.recent_days + 5))).strftime("%Y-%m-%d")

        vol_anom = self._volume_anomalies(request.min_ratio, cutoff)
        gaps = self._price_gaps(request.gap_threshold, cutoff)
        down_streaks = self._consecutive_extremes("down", 5, cutoff)
        up_streaks = self._consecutive_extremes("up", 5, cutoff)

        markdown = self._render(
            date_label,
            max_d,
            request,
            vol_anom,
            gaps,
            down_streaks,
            up_streaks,
        )
        out_path.write_text(markdown, encoding="utf-8")
        return AnomalyReportResponse(market=request.market, markdown=markdown)

    def _max_date(self):
        df = self._view_repo.execute(
            "SELECT MAX(CAST(date AS DATE)) AS max_date FROM cn.stock_prices"
        )
        if df.empty or df["max_date"].iloc[0] is None:
            return None
        value = df["max_date"].iloc[0]
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value))

    def _volume_anomalies(self, min_ratio: float, cutoff: str) -> pd.DataFrame:
        rows = self._anomaly_service.anomalies(min_ratio=min_ratio, top=30)
        df = pd.DataFrame(rows)
        if not df.empty and "date" in df.columns:
            df = df[df["date"] >= cutoff]
        return df

    def _price_gaps(self, gap_threshold: float, cutoff: str) -> pd.DataFrame:
        return self._view_repo.execute(
            """
            WITH gaps AS (
                SELECT ticker, date, open,
                    LAG(close) OVER (PARTITION BY ticker ORDER BY date) AS prev_close,
                    close
                FROM cn.stock_prices
                WHERE CAST(date AS DATE) >= ?
            ),
            gap_pct AS (
                SELECT ticker, date, open, prev_close, close,
                    ROUND(((open - prev_close) / NULLIF(prev_close, 0)) * 100, 2) AS gap_pct,
                    ROUND(((close - prev_close) / NULLIF(prev_close, 0)) * 100, 2) AS return_pct
                FROM gaps WHERE prev_close IS NOT NULL
            )
            SELECT * FROM gap_pct
            WHERE ABS(gap_pct) >= ?
            ORDER BY date DESC, ABS(gap_pct) DESC
            LIMIT 30
            """,
            [cutoff, gap_threshold],
        )

    def _consecutive_extremes(self, direction: str, min_days: int, cutoff: str) -> pd.DataFrame:
        sign = "<" if direction == "down" else ">"
        return self._view_repo.execute(
            f"""
            WITH returns AS (
                SELECT ticker, date, close,
                    LAG(close) OVER (PARTITION BY ticker ORDER BY date) AS prev_close
                FROM cn.stock_prices
                WHERE CAST(date AS DATE) >= ?
            ),
            daily AS (
                SELECT ticker, date,
                    CASE WHEN close {sign} prev_close THEN 1 ELSE 0 END AS streak_bit
                FROM returns WHERE prev_close IS NOT NULL
            ),
            streaks AS (
                SELECT ticker, date, streak_bit,
                    SUM(CASE WHEN streak_bit = 0 THEN 1 ELSE 0 END)
                        OVER (PARTITION BY ticker ORDER BY date
                              ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS reset_group
                FROM daily
            ),
            grouped AS (
                SELECT ticker,
                    MIN(date) AS from_date,
                    MAX(date) AS to_date,
                    COUNT(*) AS streak_days
                FROM streaks WHERE streak_bit = 1
                GROUP BY ticker, reset_group
                HAVING COUNT(*) >= ?
            )
            SELECT *
            FROM grouped
            WHERE CAST((SELECT MAX(date) FROM cn.stock_prices) AS DATE) - CAST(to_date AS DATE) <= ?
            ORDER BY streak_days DESC
            LIMIT 30
            """,
            [cutoff, min_days, 2],
        )

    def _render(
        self,
        date_label: str,
        max_d,
        request: GenerateAnomalyReportRequest,
        vol_anom: pd.DataFrame,
        gaps: pd.DataFrame,
        down_streaks: pd.DataFrame,
        up_streaks: pd.DataFrame,
    ) -> str:
        lines = [
            "# 异常检测报告\n",
            f"> 生成时间: {date_label} | 数据截止: {max_d} | "
            f"量比阈值: {request.min_ratio}x | 跳空阈值: {request.gap_threshold}%\n",
        ]

        lines.append("## 1. 成交量异常 (量比 >= {}x)\n".format(request.min_ratio))
        if not vol_anom.empty:
            lines.append(vol_anom.to_markdown(index=False))
        else:
            lines.append("_无符合条件的结果_")
        lines.append("\n")

        lines.append("## 2. 跳空缺口 (|跳空| >= {}%)\n".format(request.gap_threshold))
        if not gaps.empty:
            lines.append(gaps.to_markdown(index=False))
        else:
            lines.append("_无符合条件的结果_")
        lines.append("\n")

        lines.append("## 3. 连续下跌 >= 5 天 (仍在持续)\n")
        if not down_streaks.empty:
            lines.append(down_streaks.to_markdown(index=False))
        else:
            lines.append("_无符合条件的结果_")
        lines.append("\n")

        lines.append("## 4. 连续上涨 >= 5 天 (仍在持续)\n")
        if not up_streaks.empty:
            lines.append(up_streaks.to_markdown(index=False))
        else:
            lines.append("_无符合条件的结果_")
        lines.append("\n")

        return "\n".join(lines)

    def _render_empty(self, date_label: str, request: GenerateAnomalyReportRequest) -> str:
        return (
            f"# 异常检测报告\n\n"
            f"> 生成时间: {date_label} | 数据截止: _无数据_ | "
            f"量比阈值: {request.min_ratio}x | 跳空阈值: {request.gap_threshold}%\n\n"
            "_无符合条件的结果_\n"
        )
