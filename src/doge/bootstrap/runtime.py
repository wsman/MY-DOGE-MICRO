"""Runtime bootstrap container.

The bootstrap layer is the single sanctioned site where application-layer use
cases and services are wired to concrete infrastructure adapters.
``RuntimeContainer`` owns the agent/runtime factories directly (research-agent
runtimes, the runtime kernel, tool registry assembly, and the run/session/
summary/capability use cases). Product/gateway leaves it depends on are
delegated to :class:`~doge.bootstrap.gateway.GatewayContainer`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from doge.application.agent.context_builder import ContextBuilder
from doge.application.agent.model_router import ModelRouter
from doge.application.agent.runtime_kernel import RuntimeKernel
from doge.application.agent.tools import build_default_tool_registry as _build_tool_registry
from doge.application.capabilities.registry import (
    ApiCapabilityProvider,
    FeatureCapabilityProvider,
    MaturityCapabilityProvider,
    ModelProviderCapabilityProvider,
    ToolRegistryCapabilityProvider,
)
from doge.application.use_cases.capability_registry import BuildCapabilityRegistry
from doge.application.use_cases.run_summary import BuildRunSummary
from doge.application.use_cases.run_use_cases import ExecuteRun, ResumeRun
from doge.application.use_cases.session_use_cases import AppendTurn, CreateSession, ListSessions, ResumeSession
from doge.config import get_settings
from doge.infrastructure.agent.backends import KimiAgentSdkBackend
from doge.infrastructure.agent.inmemory_runtime import InMemoryResearchAgentRuntime
from doge.infrastructure.agent.persisted_runtime import PersistedResearchAgentRuntime
from doge.infrastructure.agent.scripted_model import ScriptedAgentModel
from doge.infrastructure.database.agent_repositories import (
    SQLiteApprovalRepository,
    SQLiteArtifactRepository,
    SQLiteDocumentRepository,
    SQLiteEventRepository,
    SQLiteIdempotencyStore,
    SQLiteRunQueue,
    SQLiteRunRepository,
    SQLiteSessionRepository,
)
from doge.infrastructure.database.enterprise_governance import SQLiteEnterpriseGovernanceRepository
from doge.infrastructure.database.event_subscriber import SQLiteEventSubscriber
from doge.infrastructure.database.evidence_repository import SQLiteEvidenceRepository
from doge.infrastructure.database.sqlite_runtime_transaction import (
    SQLiteOutboxRepository,
    SQLiteRuntimeTransactionFactory,
)
from doge.infrastructure.database.sqlite_uow import SQLiteAgentUnitOfWork
from doge.platform.runtime.services import (
    ArtifactEvaluationService,
    ModelExecutionService,
    ToolExecutionService,
)


@dataclass(frozen=True)
class RuntimeContainer:
    """Typed entry point for agent runtime wiring."""

    db_path: Path | str | None = None
    graph_provider: Callable[[], Any] | None = field(default=None, repr=False, compare=False)

    # ── Repository / adapter leaves ──

    def build_event_subscriber(self, *, poll_interval_seconds: float = 0.1):
        return SQLiteEventSubscriber(self.db_path, poll_interval_seconds=poll_interval_seconds)

    def build_runtime_outbox_repository(self):
        return SQLiteOutboxRepository(self.db_path)

    def build_agent_repositories(self):
        return {
            "sessions": SQLiteSessionRepository(self.db_path),
            "runs": SQLiteRunRepository(self.db_path),
            "events": SQLiteEventRepository(self.db_path),
            "artifacts": SQLiteArtifactRepository(self.db_path),
            "approvals": SQLiteApprovalRepository(self.db_path),
            "documents": SQLiteDocumentRepository(self.db_path),
            "evidence": SQLiteEvidenceRepository(self.db_path),
            "run_queue": SQLiteRunQueue(self.db_path),
            "idempotency": SQLiteIdempotencyStore(self.db_path),
            "governance": SQLiteEnterpriseGovernanceRepository(self.db_path),
        }

    def build_agent_document_repository(self):
        return SQLiteDocumentRepository(self.db_path)

    def build_agent_evidence_repository(self):
        return SQLiteEvidenceRepository(self.db_path)

    def build_agent_run_queue(self):
        return SQLiteRunQueue(self.db_path)

    def build_agent_idempotency_store(self):
        return SQLiteIdempotencyStore(self.db_path)

    def build_agent_unit_of_work(self, event_publisher: Any = None):
        return SQLiteAgentUnitOfWork(self.db_path, event_publisher=event_publisher)

    def build_create_session_use_case(self) -> CreateSession:
        return CreateSession(SQLiteSessionRepository(self.db_path))

    def build_resume_session_use_case(self) -> ResumeSession:
        return ResumeSession(SQLiteSessionRepository(self.db_path))

    def build_list_sessions_use_case(self) -> ListSessions:
        return ListSessions(SQLiteSessionRepository(self.db_path))

    def build_append_turn_use_case(self) -> AppendTurn:
        return AppendTurn(SQLiteSessionRepository(self.db_path))

    # ── Runtime factories (owned directly by the container) ──

    def build_model_router(self, document_repository=None) -> ModelRouter:
        """Build the application model router."""
        return ModelRouter(document_repository=document_repository, settings=get_settings())

    def build_agent_backends(self, secret_provider=None):
        """Build optional agent runtime backends keyed by router backend id."""
        settings = get_settings()
        secret_provider = secret_provider or self.gateway_container().build_secret_provider()
        return {
            "kimi_agent_sdk": KimiAgentSdkBackend(
                base_url=settings.kimi.effective_base_url(),
                model=settings.kimi.general_model,
                secret_provider=secret_provider,
            )
        }

    def build_agent_runtime_kernel(self, model=None, tool_registry=None, event_publisher=None) -> RuntimeKernel:
        """Build the persisted agent runtime kernel."""
        repos = self.build_agent_repositories()
        gateway = self.gateway_container()
        secret_provider = gateway.build_secret_provider()
        if model is None:
            model = (
                gateway.build_kimi_agent_model(secret_provider)
                if secret_provider.get_secret("kimi.api_key")
                else ScriptedAgentModel()
            )
        if tool_registry is None:
            tool_registry = self.build_default_tool_registry()
        model_router = self.build_model_router(document_repository=repos["documents"])
        agent_backends = self.build_agent_backends(secret_provider)
        return RuntimeKernel(
            model=model,
            tool_registry=tool_registry,
            run_repository=repos["runs"],
            event_repository=repos["events"],
            artifact_repository=repos["artifacts"],
            approval_repository=repos["approvals"],
            event_publisher=event_publisher,
            context_builder=ContextBuilder(
                document_repository=repos["documents"],
                evidence_repository=repos["evidence"],
                session_repository=repos["sessions"],
                run_repository=repos["runs"],
            ),
            model_router=model_router,
            agent_backends=agent_backends,
            governance_repository=repos["governance"],
            model_execution_service=ModelExecutionService(
                model=model,
                model_router=model_router,
                agent_backends=agent_backends,
            ),
            tool_execution_service=ToolExecutionService(
                tool_registry=tool_registry,
                governance_repository=repos["governance"],
            ),
            artifact_evaluation_service=ArtifactEvaluationService(),
            runtime_transaction_factory=SQLiteRuntimeTransactionFactory(self.db_path),
        )

    def build_research_agent_runtime(self, model: Any = None, tool_registry: Any = None) -> InMemoryResearchAgentRuntime:
        """Build the in-memory research-agent runtime for the interview demo."""
        gateway = self.gateway_container()
        secret_provider = gateway.build_secret_provider()
        if model is None:
            model = (
                gateway.build_kimi_agent_model(secret_provider)
                if secret_provider.get_secret("kimi.api_key")
                else ScriptedAgentModel()
            )
        if tool_registry is None:
            tool_registry = self.build_default_tool_registry()
        return InMemoryResearchAgentRuntime(model=model, tool_registry=tool_registry)

    def build_persisted_research_agent_runtime(
        self,
        model: Any = None,
        tool_registry: Any = None,
        event_publisher: Any = None,
    ) -> PersistedResearchAgentRuntime:
        """Build the repository-backed runtime for CLI, daemon and SDK paths."""
        return PersistedResearchAgentRuntime(
            self.build_agent_runtime_kernel(
                model=model,
                tool_registry=tool_registry,
                event_publisher=event_publisher,
            )
        )

    def build_macro_strategist_agent_use_case(self, runtime=None):
        """Build the RuntimeKernel-backed macro strategist wrapper."""
        from doge.application.use_cases.macro_strategist import MacroStrategistAgentUseCase

        if runtime is None:
            runtime = self.build_persisted_research_agent_runtime()
        return MacroStrategistAgentUseCase(runtime)

    def build_industry_analyzer_agent_use_case(self, runtime=None):
        """Build the RuntimeKernel-backed industry analyzer wrapper."""
        from doge.application.use_cases.industry_analyzer import IndustryAnalyzerAgentUseCase

        if runtime is None:
            runtime = self.build_persisted_research_agent_runtime()
        return IndustryAnalyzerAgentUseCase(runtime)

    def build_default_tool_registry(self, entitlement_checker: Any = None, context: Any = None):
        """Build the default tool registry with application dependencies injected."""
        return _build_tool_registry(
            service=self.gateway_container().build_tool_application_service(),
            entitlement_checker=entitlement_checker,
            context=context,
        )

    def build_run_summary_use_case(self, runtime: Any = None, evidence_repository: Any = None) -> BuildRunSummary:
        """Build the structured run summary/citation/eval use case."""
        if runtime is None:
            runtime = self.build_persisted_research_agent_runtime()
        if evidence_repository is None:
            evidence_repository = self.build_agent_evidence_repository()
        return BuildRunSummary(runtime, evidence_repository)

    def build_capability_registry_use_case(self) -> BuildCapabilityRegistry:
        """Build the redacted capability discovery use case."""
        settings = get_settings()
        return BuildCapabilityRegistry(
            settings,
            providers=[
                FeatureCapabilityProvider(settings),
                ModelProviderCapabilityProvider(settings),
                ApiCapabilityProvider(settings),
                MaturityCapabilityProvider(settings.project_root / "docs" / "progress" / "runtime-maturity.yaml"),
                ToolRegistryCapabilityProvider(self.build_default_tool_registry()),
            ],
        )

    def build_execute_run_use_case(self, model: Any = None, tool_registry: Any = None) -> ExecuteRun:
        runtime = self.build_persisted_research_agent_runtime(model=model, tool_registry=tool_registry)
        return ExecuteRun(runtime, SQLiteSessionRepository(self.db_path))

    def build_resume_run_use_case(self, model: Any = None, tool_registry: Any = None) -> ResumeRun:
        runtime = self.build_persisted_research_agent_runtime(model=model, tool_registry=tool_registry)
        return ResumeRun(runtime)

    # ── Bootstrap collaborators ──

    def gateway_container(self):
        """Return the graph-owned gateway container."""

        return self._process_graph().gateway_container

    def _process_graph(self):
        if self.graph_provider is not None:
            return self.graph_provider()
        from doge.bootstrap.processes import build_embedded_process

        return build_embedded_process(db_path=self.db_path)


def build_runtime_container(db_path: Path | str | None = None) -> RuntimeContainer:
    """Build the runtime container."""

    from doge.bootstrap.processes import build_embedded_process

    return build_embedded_process(db_path=db_path).runtime_container
