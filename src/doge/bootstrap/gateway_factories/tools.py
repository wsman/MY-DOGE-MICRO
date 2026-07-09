"""Gateway factory helpers for tool-service and financial-connector wiring."""
from __future__ import annotations
from doge.application.agent.tool_service import ToolApplicationService
from doge.core.ports.enterprise_governance import EnterpriseAuditEvent
from doge.infrastructure.code_execution.python import DisabledCodeExecutor, SubprocessCodeExecutor
from doge.application.services.portfolio_service import PortfolioService, RiskService, ScenarioService
from doge.config import get_settings
from doge.infrastructure.finance.local_connectors import (
    LocalNoteAnnouncementRepository,
    StaticIndustryClassificationSource,
    StaticRiskFactorSource,
    StockOverviewFinancialStatementRepository,
    UnavailableConsensusEstimateRepository,
)
from doge.bootstrap.gateway_factories.llm import build_default_text_llm_client
from doge.bootstrap.gateway_factories.market import (
    build_anomaly_service,
    build_breadth_service,
    build_ranking_service,
    build_stock_service,
    build_view_service,
)
from doge.bootstrap.gateway_factories.repositories import build_note_repository


def build_risk_factor_source():
    return StaticRiskFactorSource()


def build_industry_classification_source():
    return StaticIndustryClassificationSource()


def build_portfolio_service(workspace_container_fn):
    return PortfolioService(workspace_container_fn().build_portfolio_repository())


def build_risk_service(workspace_container_fn):
    return RiskService(
        workspace_container_fn().build_portfolio_repository(),
        build_risk_factor_source(),
    )


def build_scenario_service(workspace_container_fn):
    return ScenarioService(
        workspace_container_fn().build_portfolio_repository(),
        build_risk_factor_source(),
    )


def build_financial_statement_repository(stock_service=None):
    return StockOverviewFinancialStatementRepository(
        stock_service if stock_service is not None else build_stock_service()
    )


def build_company_announcement_repository(note_repo=None):
    return LocalNoteAnnouncementRepository(
        note_repo if note_repo is not None else build_note_repository()
    )


def build_consensus_estimate_repository():
    return UnavailableConsensusEstimateRepository()


def build_python_analysis_executor(settings=None):
    """Build the explicitly configured Python analysis executor."""
    settings = settings or get_settings()
    if not settings.features.python_analysis_enabled:
        return DisabledCodeExecutor()
    executor = settings.features.python_analysis_executor
    if executor == "subprocess":
        isolation_enabled = bool(getattr(settings.features, "slot_code_string_isolation", False))
        return SubprocessCodeExecutor(
            isolation_enabled=isolation_enabled,
            audit_sink=_code_string_resource_audit_sink(settings) if isolation_enabled else None,
        )
    return DisabledCodeExecutor()


def build_tool_application_service(
    db_path,
    runtime_container_fn,
    workspace_container_fn,
    build_rag_service_fn,
    build_generate_industry_report_use_case_fn,
) -> ToolApplicationService:
    """Build the fully injected application service used by agent tools."""
    settings = get_settings()
    guard_factory = _slot_runtime_database_factory_guard(settings)
    return ToolApplicationService(
        stock_service_factory=guard_factory(build_stock_service),
        ranking_service_factory=guard_factory(build_ranking_service),
        breadth_service_factory=guard_factory(build_breadth_service),
        anomaly_service_factory=guard_factory(build_anomaly_service),
        view_service_factory=guard_factory(build_view_service),
        portfolio_service_factory=guard_factory(lambda: build_portfolio_service(workspace_container_fn)),
        risk_service_factory=guard_factory(lambda: build_risk_service(workspace_container_fn)),
        scenario_service_factory=guard_factory(lambda: build_scenario_service(workspace_container_fn)),
        rag_service_factory=guard_factory(lambda: build_rag_service_fn(db_path, runtime_container_fn)),
        note_repository_factory=guard_factory(build_note_repository),
        industry_report_use_case_factory=guard_factory(build_generate_industry_report_use_case_fn),
        financial_statement_repository_factory=guard_factory(lambda: build_financial_statement_repository()),
        company_announcement_repository_factory=guard_factory(lambda: build_company_announcement_repository()),
        consensus_estimate_repository_factory=guard_factory(build_consensus_estimate_repository),
        industry_classification_source_factory=guard_factory(build_industry_classification_source),
        view_repository_factory=guard_factory(lambda: build_view_service()),
        code_executor=build_python_analysis_executor(settings),
        use_capability_providers=True,
    )


def _slot_runtime_database_factory_guard(settings):
    enabled = bool(getattr(settings.features, "slot_runtime_interception", False))
    if not enabled:
        return lambda factory: factory

    from doge.platform.slots import guard_database_port

    def _guard(factory):
        def _factory(*args, **kwargs):
            return guard_database_port(factory(*args, **kwargs), enabled=True)

        return _factory

    return _guard


def _code_string_resource_audit_sink(settings):
    def _append(event: dict) -> None:
        try:
            from doge.infrastructure.database.enterprise_governance import (
                SQLiteEnterpriseGovernanceRepository,
            )

            SQLiteEnterpriseGovernanceRepository(settings.db.agent_db).append_audit_event(
                EnterpriseAuditEvent(
                    event_type=str(event.get("event_type") or "slot_resource_limit_exceeded"),
                    tenant_id="local",
                    actor_hash="code-string-isolation",
                    resource_type=str(event.get("resource_type") or "code_string"),
                    resource_id=str(event.get("resource_id") or "run_python_analysis"),
                    metadata={key: value for key, value in event.items() if key != "event_type"},
                )
            )
        except Exception:
            pass

    return _append
