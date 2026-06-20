"""Generate macro report use case.

This use case owns the clean-architecture macro report workflow: gather
deterministic DuckDB-view context, ask the configured text LLM for a report, and
persist the resulting macro memo through the report repository port.
"""

from __future__ import annotations

import re
from typing import Any

from doge.application.contracts.request import GenerateMacroReportRequest
from doge.application.contracts.response import MacroReportResponse


_VALID_MARKETS = {"cn", "us"}


def _records(frame) -> list[dict[str, Any]]:
    """Convert a pandas-like DataFrame to records without leaking pandas types."""
    if frame is None:
        return []
    empty = getattr(frame, "empty", False)
    if empty:
        return []
    if hasattr(frame, "to_dict"):
        return list(frame.to_dict(orient="records"))
    return []


def _table(title: str, rows: list[dict[str, Any]], *, max_rows: int = 20) -> str:
    if not rows:
        return f"### {title}\n\n_No data available._\n"

    rows = rows[:max_rows]
    columns = list(rows[0].keys())
    header = "| " + " | ".join(str(col) for col in columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    body = []
    for row in rows:
        values = [str(row.get(col, "")) for col in columns]
        body.append("| " + " | ".join(values) + " |")
    return f"### {title}\n\n" + "\n".join([header, sep, *body]) + "\n"


def _parse_risk_signal(content: str) -> str:
    lowered = content.lower()
    if "risk-off" in lowered or "risk off" in lowered:
        return "risk-off"
    if "risk-on" in lowered or "risk on" in lowered:
        return "risk-on"
    if re.search(r"\bdefensive\b|\bcautious\b", lowered):
        return "risk-off"
    return "neutral"


def _parse_volatility(content: str) -> str:
    lowered = content.lower()
    for label in ("high", "medium", "low"):
        if re.search(rf"\b{label}\s+volatility\b|\bvolatility\s*:\s*{label}\b", lowered):
            return label
    return "low"


class GenerateMacroReportUseCase:
    """Generate a macro strategy report via an LLM client."""

    def __init__(
        self,
        view_repo,
        llm_client,
        report_repo,
    ) -> None:
        """Initialize with injected ports.

        Args:
            view_repo: An :class:`~doge.core.ports.market_view.IMarketViewRepository`.
            llm_client: An :class:`~doge.core.ports.llm.ILLMClient`.
            report_repo: An :class:`~doge.core.ports.repository.IReportRepository`.
        """
        self._view_repo = view_repo
        self._llm_client = llm_client
        self._report_repo = report_repo

    def execute(self, request: GenerateMacroReportRequest) -> MacroReportResponse:
        """Run the macro report workflow.

        The use case is intentionally offline-tolerant: missing/empty views are
        rendered as unavailable data, while an unavailable LLM returns a
        structured degraded response without writing a report.
        """
        market = (request.market or "cn").lower()
        if market not in _VALID_MARKETS:
            raise ValueError(f"unsupported market: {request.market}")

        breadth = _records(self._safe_execute(
            f"SELECT * FROM vw_market_breadth_{market} ORDER BY date DESC LIMIT ?",
            [10],
        ))
        rsrs = _records(self._safe_execute(
            f"SELECT * FROM vw_rsrs_ranking_{market} WHERE rank <= ? ORDER BY rank LIMIT ?",
            [20, 20],
        ))
        if market == "cn":
            anomalies = _records(self._safe_execute(
                """
                SELECT ticker, date, volume, avg_vol_20d, vol_ratio, intraday_return
                FROM vw_volume_anomalies_cn
                ORDER BY vol_ratio DESC
                LIMIT ?
                """,
                [10],
            ))
        else:
            anomalies = []

        system_prompt = (
            "You are a disciplined financial macro analyst. Use only the "
            "provided market-view data, cite material numbers with the format "
            "[数据: ...], and explicitly mark unavailable data instead of "
            "inventing figures. Return a concise professional markdown report "
            "with sections: Executive Summary, Market Breadth, Momentum, "
            "Volume/Risk, Risk Signal, and Watch Items."
        )
        user_prompt = self._build_prompt(
            market=market,
            breadth=breadth,
            rsrs=rsrs,
            anomalies=anomalies,
            custom_prompt=request.custom_prompt,
        )

        content = self._llm_client.chat(
            system_prompt,
            user_prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )
        if not content:
            return MacroReportResponse(
                analyst=request.analyst_model,
                error="LLM unavailable",
            )

        risk_signal = _parse_risk_signal(content)
        volatility = _parse_volatility(content)
        self._report_repo.save_macro_report(
            content=content,
            risk_signal=risk_signal,
            volatility=volatility,
            tags=f"Macro, {market.upper()}, CleanArchitecture",
            analyst=request.analyst_model,
        )
        return MacroReportResponse(
            content=content,
            risk_signal=risk_signal,
            volatility=volatility,
            tags=f"Macro, {market.upper()}, CleanArchitecture",
            analyst=request.analyst_model,
        )

    def _safe_execute(self, sql: str, params: list[Any]):
        try:
            return self._view_repo.execute(sql, params)
        except Exception:
            return None

    def _build_prompt(
        self,
        *,
        market: str,
        breadth: list[dict[str, Any]],
        rsrs: list[dict[str, Any]],
        anomalies: list[dict[str, Any]],
        custom_prompt: str | None,
    ) -> str:
        sections = [
            f"# Macro context for market={market}",
            _table(f"Market breadth, recent 10 rows (source: vw_market_breadth_{market})", breadth, max_rows=10),
            _table(f"RSRS ranking, top 20 (source: vw_rsrs_ranking_{market})", rsrs, max_rows=20),
            _table(
                "Volume anomalies, top 10 (source: vw_volume_anomalies_cn)",
                anomalies,
                max_rows=10,
            ),
        ]
        if market == "us":
            sections.append(
                "### Volume anomalies note\n\n"
                "_The current repository defines only vw_volume_anomalies_cn; "
                "US volume anomaly data is unavailable in this workflow._\n"
            )
        if custom_prompt:
            sections.append(f"### Operator prompt\n\n{custom_prompt}\n")
        return "\n\n".join(sections)
