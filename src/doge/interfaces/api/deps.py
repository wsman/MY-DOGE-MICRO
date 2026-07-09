"""FastAPI dependency providers for the API interface layer.

This module is the **single sanctioned site** where API routers import
application-layer factories. Routers MUST NOT import ``sqlite3``, ``duckdb``,
or any legacy connection helper directly; they request a port/use case via
``Depends(deps.get_*)`` and this module wires the default adapter through
``doge.bootstrap`` containers.
"""

import logging
import os

from fastapi import Depends, Header, HTTPException, Request

from doge.config import Settings, get_settings
from doge.interfaces.api import factories
from doge.interfaces.api.container import app_container as _container
from doge.core.ports.metadata import ITickerMetadataSource
from doge.core.ports.repository import IReportRepository, ISchemaBrowser, IStockRepository, INoteRepository
from doge.core.ports.tdx_server_list import ITDXServerList
from doge.infrastructure.auth import DenyAllEnterpriseAuthProvider, build_enterprise_auth_provider

_research_agent_runtime = None
_persisted_research_agent_runtime = None
_event_bus = None
_event_subscriber = None
_worker = None
_run_queue = None
_idempotency_store = None
_agent_unit_of_work = None
_runtime_outbox_publisher = None
_file_upload_service = None
_enterprise_governance_repository = None
_slot_activation_repository = None
_run_scope_resolver = None
_research_agent_runtime_warning_emitted = False

logger = logging.getLogger(__name__)


def get_settings_dep() -> Settings:
    """Return the current ``Settings`` singleton."""
    return get_settings()


def get_app_container():
    """Return the API bootstrap container."""
    return _container


def has_oidc_config(auth_config) -> bool:
    """Return whether the configured enterprise auth mode has OIDC/JWKS inputs."""

    return bool(auth_config.oidc_issuer and auth_config.oidc_audience and auth_config.oidc_jwks_url)


def build_api_auth_provider(settings, secret_provider_factory=None):
    """Build API enterprise auth through the sanctioned API composition site."""

    if secret_provider_factory is None:
        secret_provider_factory = _container.gateway.build_secret_provider
    secret_provider = None
    if settings.auth.mode == "enterprise" and not has_oidc_config(settings.auth):
        secret_provider = secret_provider_factory()
    return build_enterprise_auth_provider(settings.auth, secret_provider=secret_provider)


def is_deny_all_enterprise_auth_provider(auth_provider) -> bool:
    """Hide the infrastructure auth class check behind the deps boundary."""

    return isinstance(auth_provider, DenyAllEnterpriseAuthProvider)


def get_report_repository() -> IReportRepository:
    """Provide the default SQLite-backed report repository."""
    return _container.gateway.build_report_repository()


def get_schema_browser() -> ISchemaBrowser:
    """Provide the default SQLite-backed schema browser."""
    return _container.gateway.build_schema_browser()


def get_stock_repository() -> IStockRepository:
    """Provide the default DuckDB-backed stock repository."""
    return _container.gateway.build_stock_repository()


def get_note_repository() -> INoteRepository:
    """Provide the default SQLite-backed note repository."""
    return _container.gateway.build_note_repository()


def get_manage_notes_use_case():
    """Provide the default ``ManageNotesUseCase``."""
    return _container.gateway.build_manage_notes_use_case()


def get_generate_macro_report_use_case():
    """Provide the default ``GenerateMacroReportUseCase``."""
    return _container.gateway.build_generate_macro_report_use_case()


def get_generate_industry_report_use_case():
    """Provide the default ``GenerateIndustryReportUseCase``."""
    return _container.gateway.build_generate_industry_report_use_case()


def get_research_agent_runtime():
    """Provide the process-local in-memory research agent runtime."""
    global _research_agent_runtime, _research_agent_runtime_warning_emitted
    if _research_agent_runtime is None:
        if not _research_agent_runtime_warning_emitted:
            logger.warning(
                "creating legacy in-memory research agent runtime; "
                "new daemon, SDK, and platform flows must use persisted runtime state"
            )
            _research_agent_runtime_warning_emitted = True
        _research_agent_runtime = _container.runtime.build_research_agent_runtime()
    return _research_agent_runtime


def get_event_bus():
    """Provide the in-process event bus for daemon/v1 streams."""
    global _event_bus
    if _event_bus is None:
        _event_bus = factories.build_event_bus()
    return _event_bus


def get_event_subscriber():
    """Provide the cross-process-safe runtime event subscriber."""
    global _event_subscriber
    if _event_subscriber is None:
        _event_subscriber = _container.runtime.build_event_subscriber()
    return _event_subscriber


def get_persisted_research_agent_runtime():
    """Provide the repository-backed research agent runtime."""
    global _persisted_research_agent_runtime
    if _persisted_research_agent_runtime is None:
        _persisted_research_agent_runtime = _container.runtime.build_persisted_research_agent_runtime(
            event_publisher=get_event_bus()
        )
    return _persisted_research_agent_runtime


def get_agent_document_repository():
    """Provide the persisted document repository."""
    return _container.runtime.build_agent_document_repository()


def get_file_upload_service():
    """Provide the shared file upload service."""
    global _file_upload_service
    if _file_upload_service is None:
        _file_upload_service = _container.gateway.build_file_upload_service()
    return _file_upload_service


def get_agent_evidence_repository():
    """Provide the persisted evidence repository."""
    return _container.runtime.build_agent_evidence_repository()


def get_run_summary_use_case():
    """Provide the structured run summary/citation/eval use case."""
    return _container.runtime.build_run_summary_use_case(
        runtime=get_persisted_research_agent_runtime(),
        evidence_repository=get_agent_evidence_repository(),
    )


def get_capability_registry_use_case():
    """Provide the redacted capability discovery use case."""
    return _container.runtime.build_capability_registry_use_case()


def get_slot_status_rows(settings: Settings | None = None):
    """Return read-only built-in slot status rows for API/operator diagnostics."""

    from doge.bootstrap.runtime_factories.slots import build_slot_status_rows

    return build_slot_status_rows(settings if settings is not None else get_settings())


def get_slot_bundle_rows(settings: Settings | None = None, activation_repo=None):
    """Return read-only built-in slot bundle rows for API/operator diagnostics."""

    from doge.bootstrap.runtime_factories.slots import build_slot_bundle_rows

    return build_slot_bundle_rows(
        settings if settings is not None else get_settings(),
        activation_repo=activation_repo or get_slot_activation_repository(),
    )


def activate_slot_bundle(
    bundle_id: str,
    settings: Settings | None = None,
    *,
    actor_hash: str = "local-api",
    tenant_id: str = "local",
    request_id: str | None = None,
    activation_repo=None,
    governance_repo=None,
):
    """Activate a slot bundle."""

    from doge.bootstrap.runtime_factories.slots import activate_slot_bundle

    return activate_slot_bundle(
        bundle_id,
        settings if settings is not None else get_settings(),
        activation_repo=activation_repo or get_slot_activation_repository(),
        governance_repo=governance_repo or get_enterprise_governance_repository(),
        actor_hash=actor_hash,
        tenant_id=tenant_id,
        request_id=request_id,
    )


def deactivate_slot_bundle(
    settings: Settings | None = None,
    *,
    actor_hash: str = "local-api",
    tenant_id: str = "local",
    request_id: str | None = None,
    activation_repo=None,
    governance_repo=None,
):
    """Deactivate the current slot bundle."""

    from doge.bootstrap.runtime_factories.slots import deactivate_slot_bundle

    return deactivate_slot_bundle(
        settings if settings is not None else get_settings(),
        activation_repo=activation_repo or get_slot_activation_repository(),
        governance_repo=governance_repo or get_enterprise_governance_repository(),
        actor_hash=actor_hash,
        tenant_id=tenant_id,
        request_id=request_id,
    )


def install_slot(
    source: str,
    settings: Settings | None = None,
    *,
    actor_hash: str = "local-api",
    tenant_id: str = "local",
    request_id: str | None = None,
    governance_repo=None,
):
    """Install a slot manifest through the server-side slot installer."""

    from doge.bootstrap.runtime_factories.slots import install_slot

    return install_slot(
        source,
        settings if settings is not None else get_settings(),
        governance_repo=governance_repo or get_enterprise_governance_repository(),
        actor_hash=actor_hash,
        tenant_id=tenant_id,
        request_id=request_id,
    )


def get_slot_ui_panel_rows(
    settings: Settings | None = None,
    *,
    workspace: str | None = None,
    zone: str | None = None,
    mode: str | None = None,
):
    """Return read-only UI panel rows for Web/workspace discovery."""

    from doge.bootstrap.runtime_factories.slots import build_slot_ui_panel_rows

    return build_slot_ui_panel_rows(
        settings if settings is not None else get_settings(),
        workspace=workspace,
        zone=zone,
        mode=mode,
    )


def get_portfolio_repository():
    """Provide the persisted portfolio repository."""
    return _container.workspace.build_portfolio_repository()


def get_platform_repository():
    """Provide the platform workspace/project/case/template repository."""
    return _container.workspace.build_platform_repository()


def get_portfolio_import_service(portfolio_repository=Depends(get_portfolio_repository)):
    """Provide the CSV portfolio import service."""
    return factories.build_portfolio_import_service(portfolio_repository)


def get_portfolio_summary_service(portfolio_repository=Depends(get_portfolio_repository)):
    """Provide the portfolio import summary service."""
    return factories.build_portfolio_summary_service(portfolio_repository)


def get_enterprise_governance_repository():
    """Provide enterprise ACL and audit repository."""
    global _enterprise_governance_repository
    if _enterprise_governance_repository is None:
        _enterprise_governance_repository = _container.workspace.build_enterprise_governance_repository()
    return _enterprise_governance_repository


def get_slot_activation_repository():
    """Provide persisted slot bundle activation state."""
    global _slot_activation_repository
    if _slot_activation_repository is None:
        _slot_activation_repository = _container.workspace.build_slot_activation_repository()
    return _slot_activation_repository


def get_agent_session_repository():
    """Provide the persisted session repository."""
    return _container.runtime.build_agent_repositories()["sessions"]


def get_run_queue():
    """Provide the durable agent run queue."""
    global _run_queue
    if _run_queue is None:
        _run_queue = _container.runtime.build_agent_run_queue()
    return _run_queue


def get_idempotency_store():
    """Provide the durable idempotency-key store."""
    global _idempotency_store
    if _idempotency_store is None:
        _idempotency_store = _container.runtime.build_agent_idempotency_store()
    return _idempotency_store


def get_agent_unit_of_work():
    """Provide the transactional unit of work for daemon enqueue."""
    global _agent_unit_of_work
    if _agent_unit_of_work is None:
        _agent_unit_of_work = _container.runtime.build_agent_unit_of_work(event_publisher=get_event_bus())
    return _agent_unit_of_work


def get_runtime_outbox_publisher():
    """Provide the optional transactional outbox publisher loop."""
    global _runtime_outbox_publisher
    if _runtime_outbox_publisher is None:
        _runtime_outbox_publisher = factories.build_runtime_outbox_publisher(
            _container.runtime.build_runtime_outbox_repository(),
            get_event_bus(),
        )
    return _runtime_outbox_publisher


def get_daemon_readiness_probe():
    """Provide the daemon readiness probe for API health routes."""

    from doge.infrastructure.database.readiness import SQLiteRuntimeReadinessProbe

    return SQLiteRuntimeReadinessProbe(settings=get_settings())


def get_existing_daemon_worker():
    """Return the daemon worker only if this process already created it."""

    return _worker


def get_run_scope_resolver():
    """Provide a scope resolver that reads run header identity metadata directly."""
    global _run_scope_resolver
    if _run_scope_resolver is None:
        from doge.infrastructure.database.run_scope_resolver import SQLiteRunScopeResolver

        _run_scope_resolver = SQLiteRunScopeResolver(_container.runtime.db_path)
    return _run_scope_resolver


def get_daemon_worker():
    """Provide the singleton daemon worker."""
    global _worker
    if _worker is None:
        settings = get_settings()
        _worker = factories.build_daemon_worker(
            runtime=get_persisted_research_agent_runtime(),
            session_repository=get_agent_session_repository(),
            run_queue=get_run_queue(),
            idempotency_store=get_idempotency_store(),
            unit_of_work=get_agent_unit_of_work(),
            scope_resolver=get_run_scope_resolver(),
            auto_start=settings.daemon.process_role != "api",
        )
    return _worker


def require_api_token(authorization: str | None = Header(default=None)):
    """Require bearer auth only when DOGE_API_TOKEN is configured."""
    expected = os.environ.get("DOGE_API_TOKEN")
    if not expected:
        return None
    if authorization != f"Bearer {expected}":
        raise HTTPException(401, "unauthorized")
    return None


def get_metadata_source() -> ITickerMetadataSource:
    """Provide the default yfinance-backed ticker metadata source."""
    return _container.gateway.build_metadata_source()


def get_storage_repository():
    """Provide the single-logical-writer SQLite storage repository.

    Used by the scan router for schema bootstrap. Exposed here so the router
    does not import an infrastructure adapter directly.
    """
    return _container.gateway.build_storage_repository()


def get_tdx_server_list() -> ITDXServerList:
    """Provide the configured TDX server directory adapter."""
    return _container.gateway.build_tdx_server_list()


def get_request_state(request: Request) -> dict:
    """Expose FastAPI request state to handlers that need it."""
    return request.state
