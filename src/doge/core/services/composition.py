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
from doge.core.services.anomaly_service import AnomalyService
from doge.core.services.breadth_service import BreadthService
from doge.core.services.ranking_service import RankingService
from doge.core.services.view_service import ViewService

# Infrastructure import is intentionally localized to this composition root.
from doge.infrastructure.database.market_view_repository import (
    DuckDBMarketViewRepository,
)


def build_view_repository(read_only: bool = True) -> IMarketViewRepository:
    """Construct the default read-only DuckDB market-view repository."""
    return DuckDBMarketViewRepository(read_only=read_only)


def build_view_service(
    repo: IMarketViewRepository | None = None,
) -> ViewService:
    """Build a :class:`ViewService` with an injected (or default) repository."""
    return ViewService(repo if repo is not None else build_view_repository())


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
