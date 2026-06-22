"""SQLite portfolio repository."""

from __future__ import annotations

from pathlib import Path

from doge.config import get_settings
from doge.core.domain.portfolio_models import Portfolio, PortfolioHolding
from doge.core.ports.portfolio_repository import IPortfolioRepository
from doge.infrastructure.database.agent_repositories import bootstrap_agent_schema
from doge.infrastructure.database.sqlite import SQLiteConnection


class SQLitePortfolioRepository(IPortfolioRepository):
    def __init__(self, db_path: Path | str | None = None) -> None:
        self._db_path = Path(db_path) if db_path is not None else get_settings().db.agent_db
        bootstrap_agent_schema(self._db_path)
        self._connection = SQLiteConnection(self._db_path, use_row_factory=True)

    def _connect(self):
        return self._connection.connect()

    def save(self, portfolio: Portfolio, tenant_id: str | None = None) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO portfolios(portfolio_id, tenant_id, name, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(portfolio_id) DO UPDATE SET
                    tenant_id = excluded.tenant_id,
                    name = excluded.name,
                    updated_at = excluded.updated_at
                """,
                (portfolio.portfolio_id, tenant_id, portfolio.name),
            )
            conn.execute("DELETE FROM portfolio_holdings WHERE portfolio_id = ?", (portfolio.portfolio_id,))
            for holding in portfolio.holdings:
                conn.execute(
                    """
                    INSERT INTO portfolio_holdings(
                        portfolio_id, symbol, asset_class, sector, quantity, market_value, currency
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        portfolio.portfolio_id,
                        holding.symbol,
                        holding.asset_class,
                        holding.sector,
                        holding.quantity,
                        holding.market_value,
                        holding.currency,
                    ),
                )
            conn.commit()

    def get(self, portfolio_id: str, tenant_id: str | None = None) -> Portfolio | None:
        sql = "SELECT * FROM portfolios WHERE portfolio_id = ?"
        params: tuple[str, ...] = (portfolio_id,)
        if tenant_id is not None:
            sql += " AND tenant_id = ?"
            params = (portfolio_id, tenant_id)
        with self._connect() as conn:
            row = conn.execute(sql, params).fetchone()
            if row is None:
                return None
            holdings = [
                PortfolioHolding.from_mapping(dict(item))
                for item in conn.execute(
                    "SELECT * FROM portfolio_holdings WHERE portfolio_id = ? ORDER BY symbol ASC",
                    (portfolio_id,),
                ).fetchall()
            ]
        return Portfolio(portfolio_id=row["portfolio_id"], name=row["name"], holdings=holdings)


def demo_portfolio() -> Portfolio:
    return Portfolio(
        portfolio_id="portfolio-demo",
        name="Demo balanced portfolio",
        holdings=[
            PortfolioHolding("AAPL", "equity", "technology", 25000.0, quantity=120),
            PortfolioHolding("MSFT", "equity", "technology", 22000.0, quantity=80),
            PortfolioHolding("TLT", "bond", "rates", 18000.0, quantity=200),
            PortfolioHolding("CASH", "cash", "cash", 5000.0, quantity=5000),
        ],
    )
