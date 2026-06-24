"""Stateless factory helpers for the API dependency layer.

These helpers assemble application-layer services from already-wired ports.
They hold no process-local state and import no infrastructure adapters, no
FastAPI primitives -- only application-layer classes -- so ``deps.py`` stays
the single sanctioned infrastructure import site and can delegate assembly
here.
"""

from __future__ import annotations

from typing import Any


def build_portfolio_import_service(portfolio_repository: Any):
    """Build the CSV portfolio import service bound to a portfolio repository."""
    from doge.application.services.portfolio_import_service import PortfolioImportService

    return PortfolioImportService(portfolio_repository)


def build_event_bus():
    """Build the in-process event bus used by daemon/v1 streams."""
    from doge.application.agent.event_bus import EventBus

    return EventBus()


def build_daemon_worker(
    *,
    runtime: Any,
    session_repository: Any,
    run_queue: Any,
    idempotency_store: Any,
    unit_of_work: Any,
    auto_start: bool,
):
    """Build the singleton asyncio daemon worker from its wired collaborators."""
    from doge.application.agent.worker import AsyncioWorker

    return AsyncioWorker(
        runtime,
        session_repository,
        run_queue,
        idempotency_store,
        unit_of_work,
        auto_start=auto_start,
    )


def build_runtime_outbox_publisher(outbox_repository: Any, event_bus: Any):
    """Build the optional transactional outbox publisher loop."""
    from doge.application.agent.outbox_publisher import OutboxPublisher

    return OutboxPublisher(outbox_repository, event_bus)
