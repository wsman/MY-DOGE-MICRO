"""SQLite portfolio repository."""

from __future__ import annotations

from pathlib import Path

from doge.config import get_settings
from doge.core.domain.portfolio_models import Portfolio, PortfolioHolding
from doge.core.ports.portfolio_repository import IPortfolioRepository
from doge.infrastructure.database.agent_repositories import bootstrap_agent_schema
from doge.infrastructure.database.sqlite import SQLiteConnection
from doge.infrastructure.database.tenant_guard import LOCAL_TENANT_ID, guard_existing_tenant, resolve_tenant_id
from doge.shared.scope import TenantScope


class SQLitePortfolioRepository(IPortfolioRepository):
    def __init__(self, db_path: Path | str | None = None) -> None:
        self._db_path = Path(db_path) if db_path is not None else get_settings().db.agent_db
        bootstrap_agent_schema(self._db_path)
        self._connection = SQLiteConnection(self._db_path, use_row_factory=True)

    def _connect(self):
        return self._connection.connect()

    def save(
        self,
        portfolio: Portfolio,
        scope: TenantScope | str | None = None,
        *,
        tenant_id: str | None = None,
    ) -> None:
        requested_tenant_id = _tenant_id_from_scope(scope, tenant_id)
        effective_tenant_id = resolve_tenant_id(requested_tenant_id)
        with self._connect() as conn:
            guard_existing_tenant(
                conn,
                table="portfolios",
                key_column="portfolio_id",
                key_value=portfolio.portfolio_id,
                tenant_id=effective_tenant_id,
            )
            conn.execute(
                """
                INSERT INTO portfolios(portfolio_id, tenant_id, name, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(portfolio_id) DO UPDATE SET
                    tenant_id = excluded.tenant_id,
                    name = excluded.name,
                    updated_at = excluded.updated_at
                """,
                (portfolio.portfolio_id, effective_tenant_id, portfolio.name),
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

    def get(
        self,
        portfolio_id: str,
        scope: TenantScope | str | None = None,
        *,
        tenant_id: str | None = None,
    ) -> Portfolio | None:
        sql = "SELECT * FROM portfolios WHERE portfolio_id = ?"
        requested_tenant_id = _tenant_id_from_scope(scope, tenant_id)
        tenant_sql, tenant_params = _tenant_filter("tenant_id", requested_tenant_id)
        sql += tenant_sql
        params: tuple[str, ...] = (portfolio_id, *tenant_params)
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


def _tenant_id_from_scope(scope: TenantScope | str | None, tenant_id: str | None = None) -> str | None:
    if isinstance(scope, TenantScope):
        if tenant_id is not None and tenant_id != scope.tenant_id:
            raise ValueError(f"tenant mismatch for scope: {tenant_id} != {scope.tenant_id}")
        return scope.tenant_id
    if isinstance(scope, str):
        if tenant_id is not None and tenant_id != scope:
            raise ValueError(f"tenant mismatch for scope: {tenant_id} != {scope}")
        return scope
    return tenant_id


def _tenant_filter(column: str, tenant_id: str | None, *, prefix: str = " AND ") -> tuple[str, tuple[str, ...]]:
    if tenant_id is None:
        return "", ()
    if tenant_id == LOCAL_TENANT_ID:
        return f"{prefix}({column} = ? OR {column} IS NULL)", (LOCAL_TENANT_ID,)
    return f"{prefix}{column} = ?", (tenant_id,)


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
