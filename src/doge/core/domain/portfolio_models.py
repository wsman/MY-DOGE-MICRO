"""Portfolio domain models for deterministic finance tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PortfolioHolding:
    symbol: str
    asset_class: str
    sector: str
    market_value: float
    quantity: float = 0.0
    currency: str = "USD"

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "asset_class": self.asset_class,
            "sector": self.sector,
            "quantity": self.quantity,
            "market_value": self.market_value,
            "currency": self.currency,
        }

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "PortfolioHolding":
        return cls(
            symbol=data["symbol"],
            asset_class=data.get("asset_class") or "equity",
            sector=data.get("sector") or "unknown",
            quantity=float(data.get("quantity") or 0.0),
            market_value=float(data.get("market_value") or 0.0),
            currency=data.get("currency") or "USD",
        )


@dataclass(frozen=True)
class Portfolio:
    portfolio_id: str
    name: str
    holdings: list[PortfolioHolding] = field(default_factory=list)

    @property
    def total_market_value(self) -> float:
        return sum(holding.market_value for holding in self.holdings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "portfolio_id": self.portfolio_id,
            "name": self.name,
            "total_market_value": self.total_market_value,
            "holdings": [holding.to_dict() for holding in self.holdings],
        }

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "Portfolio":
        return cls(
            portfolio_id=data["portfolio_id"],
            name=data.get("name") or data["portfolio_id"],
            holdings=[PortfolioHolding.from_mapping(item) for item in data.get("holdings", [])],
        )
