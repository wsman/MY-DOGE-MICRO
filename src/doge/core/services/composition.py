"""Composition root for the view-backed services.

This module is the **single site** where the ``IMarketViewRepository`` port is
wired to its concrete ``DuckDBMarketViewRepository`` adapter and injected into
the read-only view-backed services. The services themselves import no
infrastructure (ADR-0010 / clean-architecture-migration AC-2); only this
factory module does.

Interface layers (MCP tools, API routers, CLI) should construct these services
via the ``build_*`` functions here rather than wiring adapters directly, so the
layer invariant stays grep-able.
"""

from doge.core.ports.market_view import IMarketViewRepository
from doge.core.ports.repository import IStockRepository
from doge.core.services.anomaly_service import AnomalyService
from doge.core.services.breadth_service import BreadthService
from doge.core.services.ranking_service import RankingService
from doge.core.services.stock_service import StockService
from doge.core.services.view_service import ViewService

# Infrastructure import is intentionally localized to this composition root.
from doge.infrastructure.database.market_view_repository import (
    DuckDBMarketViewRepository,
)
from doge.infrastructure.database.repositories import DuckDBStockRepository


def build_view_repository(read_only: bool = True) -> IMarketViewRepository:
    """Construct the default read-only DuckDB market-view repository."""
    return DuckDBMarketViewRepository(read_only=read_only)


def build_view_service(
    repo: IMarketViewRepository | None = None,
) -> ViewService:
    """Build a :class:`ViewService` with an injected (or default) repository."""
    return ViewService(repo if repo is not None else build_view_repository())


def build_stock_repository(read_only: bool = True) -> IStockRepository:
    """Construct the default read-only DuckDB stock repository.

    The ``read_only`` flag mirrors :func:`build_view_repository`; the
    :class:`~doge.infrastructure.database.repositories.DuckDBStockRepository`
    adapter is read-only by design (single-logical-writer principle), so
    callers should leave the default.
    """
    return DuckDBStockRepository()


def build_stock_service(
    repo: IStockRepository | None = None,
) -> StockService:
    """Build a :class:`StockService` with an injected (or default) repository.

    The stock service depends on :class:`IStockRepository` (a different port
    than :class:`IMarketViewRepository`) so it has its own factory; this is the
    single sanctioned site for the ``DuckDBStockRepository`` adapter wiring.
    """
    return StockService(repo if repo is not None else build_stock_repository())


def build_ranking_service(
    repo: IMarketViewRepository | None = None,
) -> RankingService:
    """Build a :class:`RankingService` with an injected (or default) repository."""
    return RankingService(repo if repo is not None else build_view_repository())


def build_breadth_service(
    repo: IMarketViewRepository | None = None,
) -> BreadthService:
    """Build a :class:`BreadthService` with an injected (or default) repository."""
    return BreadthService(repo if repo is not None else build_view_repository())


def build_anomaly_service(
    repo: IMarketViewRepository | None = None,
) -> AnomalyService:
    """Build an :class:`AnomalyService` with an injected (or default) repository."""
    return AnomalyService(repo if repo is not None else build_view_repository())


def refresh_views() -> None:
    """Materialize the DuckDB analytical views after a market-data scan.

    Replaces the interface-layer DuckDB-connect / view-DDL calls that used to
    live directly inside ``src/api/routers/scan.py`` (an ADR-0001 forbidden
    pattern; S002-005 / TR-011). The DuckDB materialization is delegated to
    the clean :class:`~doge.infrastructure.database.duckdb.DuckDBConnection`
    adapter's own ``refresh_views`` (the canonical runner for
    ``data/views.sql``), so behavior is preserved while the literal forbidden
    symbols stay out of the interface layer.

    This function lives in the composition root — the single sanctioned site
    for an infrastructure import (ADR-0010 AC-2: service modules import no
    infrastructure; only this factory module does).

    Raises:
        Exception: Any failure from the underlying DuckDB materialization is
            propagated unchanged so callers can log it (the interface layer
            logs at WARNING via :func:`logging.warning` — see scan.py). It is
            deliberately NOT swallowed here so a refresh failure is observable
            (the server-side half of the S002-010 stuck-running concern).
    """
    from doge.infrastructure.database.duckdb import DuckDBConnection

    # The adapter's refresh_views opens its own write-mode connection and
    # closes it; we do not hold a long-lived connection here.
    DuckDBConnection(read_only=False).refresh_views()
