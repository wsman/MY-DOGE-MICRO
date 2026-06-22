"""CSV import service for local research portfolios."""

from __future__ import annotations

import csv
import io
from uuid import uuid4

from doge.core.domain.portfolio_models import Portfolio, PortfolioHolding
from doge.core.ports.portfolio_repository import IPortfolioRepository


class PortfolioImportError(ValueError):
    """Safe, user-facing portfolio import validation error."""


class PortfolioImportService:
    """Parse a holdings CSV and persist it as a portfolio."""

    def __init__(self, repository: IPortfolioRepository) -> None:
        self._repository = repository

    def import_csv(
        self,
        content: str,
        *,
        name: str | None = None,
        portfolio_id: str | None = None,
        tenant_id: str | None = None,
    ) -> dict:
        rows = list(csv.DictReader(io.StringIO(content)))
        if not rows:
            raise PortfolioImportError("portfolio csv has no holdings")

        holdings = [_holding_from_row(row, index) for index, row in enumerate(rows, start=2)]
        portfolio = Portfolio(
            portfolio_id=portfolio_id or f"portfolio-{uuid4().hex[:12]}",
            name=name or "Imported portfolio",
            holdings=holdings,
        )
        self._repository.save(portfolio, tenant_id=tenant_id)
        result = portfolio.to_dict()
        if tenant_id is not None:
            result["tenant_id"] = tenant_id
        return result


def _holding_from_row(row: dict[str, str | None], line_number: int) -> PortfolioHolding:
    normalized = {str(key or "").strip().lower(): value for key, value in row.items()}
    symbol = _text(normalized, "symbol", "ticker")
    if not symbol:
        raise PortfolioImportError(f"line {line_number}: symbol is required")
    market_value = _number(normalized, line_number, "market_value", "value", "market value")
    if market_value <= 0:
        raise PortfolioImportError(f"line {line_number}: market_value must be positive")
    return PortfolioHolding(
        symbol=symbol.upper(),
        asset_class=_text(normalized, "asset_class", "asset class") or "equity",
        sector=_text(normalized, "sector", "industry") or "unknown",
        quantity=_number(normalized, line_number, "quantity", default=0.0),
        market_value=market_value,
        currency=(_text(normalized, "currency") or "USD").upper(),
    )


def _text(row: dict[str, str | None], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _number(
    row: dict[str, str | None],
    line_number: int,
    *keys: str,
    default: float | None = None,
) -> float:
    for key in keys:
        value = row.get(key)
        if value is None or str(value).strip() == "":
            continue
        try:
            return float(str(value).replace(",", "").strip())
        except ValueError as exc:
            raise PortfolioImportError(f"line {line_number}: {key} must be numeric") from exc
    if default is not None:
        return default
    joined = " or ".join(keys)
    raise PortfolioImportError(f"line {line_number}: {joined} is required")
