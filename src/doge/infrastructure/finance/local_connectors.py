"""Local fallback implementations for financial connector ports."""

from __future__ import annotations

from typing import Any


class StockOverviewFinancialStatementRepository:
    """Fallback statement adapter backed by the local stock overview service."""

    def __init__(self, stock_service) -> None:
        self._stock_service = stock_service

    def get_statement(self, ticker: str, statement_type: str = "income", period: str = "annual") -> dict[str, Any]:
        overview = self._stock_service.overview(ticker, "us") or {}
        fields = {
            key: value
            for key, value in overview.items()
            if isinstance(value, (int, float, str)) and key not in {"ticker", "market", "status"}
        }
        status = "fallback" if fields else "provider_unavailable"
        return {
            "ticker": ticker,
            "statement_type": statement_type,
            "period": period,
            "provider": "local_stock_overview",
            "provider_status": status,
            "freshness": "local_cache",
            "fields": fields,
            "message": (
                "Formal financial statement connector is not configured; "
                "fields are derived from local stock overview fallback."
            ),
        }


class LocalNoteAnnouncementRepository:
    """Fallback announcement adapter backed by local notes."""

    def __init__(self, note_repository) -> None:
        self._note_repository = note_repository

    def list_announcements(self, ticker: str, limit: int = 5) -> dict[str, Any]:
        rows = self._note_repository.search_notes(ticker, limit=limit)
        return {
            "ticker": ticker,
            "limit": limit,
            "provider": "local_notes",
            "provider_status": "fallback" if rows else "provider_unavailable",
            "freshness": "local_cache",
            "announcements": rows[:limit],
            "message": (
                "Exchange disclosure connector is not configured; "
                "local research notes are used as fallback."
            ),
        }


class UnavailableConsensusEstimateRepository:
    """Typed unavailable adapter for consensus estimates."""

    def compare_estimates(self, ticker: str, metric: str = "eps") -> dict[str, Any]:
        return {
            "ticker": ticker,
            "metric": metric,
            "provider": "consensus",
            "provider_status": "provider_unavailable",
            "estimates": [],
            "message": "Consensus connector is not configured in this local reference implementation.",
        }


class StaticIndustryClassificationSource:
    """Small deterministic classification source for local demos."""

    _SECTORS = {
        "AAPL": ("technology", "consumer electronics"),
        "MSFT": ("technology", "software"),
        "NVDA": ("technology", "semiconductors"),
        "TSLA": ("consumer discretionary", "automobiles"),
        "TLT": ("rates", "fixed income"),
        "CASH": ("cash", "cash"),
    }

    def classify(self, ticker: str, market: str = "us") -> dict[str, Any]:
        sector, industry = self._SECTORS.get(ticker.upper(), ("unknown", "unknown"))
        return {
            "ticker": ticker,
            "market": market,
            "sector": sector,
            "industry": industry,
            "provider": "static_local_classification",
            "provider_status": "fallback" if sector != "unknown" else "provider_unavailable",
        }


class StaticRiskFactorSource:
    """Configurable deterministic assumptions for demo risk tools."""

    _VOLATILITY = {"equity": 0.22, "bond": 0.08, "cash": 0.01}
    _DRAWDOWN = {"equity": 0.35, "bond": 0.12, "cash": 0.0}
    _DURATION = {"bond": 7.0}

    def asset_volatility(self, asset_class: str) -> float:
        return self._VOLATILITY.get(asset_class, 0.15)

    def asset_drawdown(self, asset_class: str) -> float:
        return self._DRAWDOWN.get(asset_class, 0.2)

    def asset_duration(self, asset_class: str) -> float:
        return self._DURATION.get(asset_class, 0.0)
