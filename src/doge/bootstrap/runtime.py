"""Runtime bootstrap container facade."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from doge.bootstrap.runtime_factories import agent_use_cases
from doge.bootstrap.runtime_factories import repositories
from doge.bootstrap.runtime_factories import runtime_kernel
from doge.bootstrap.runtime_factories import tools
from doge.bootstrap.runtime_factories import use_cases


@dataclass(frozen=True)
class RuntimeContainer:
    """Typed entry point for agent runtime wiring."""

    db_path: Path | str | None = None
    graph_provider: Callable[[], Any] | None = field(default=None, repr=False, compare=False)

    # -- Repository / adapter leaves --
    def build_event_subscriber(self, *, poll_interval_seconds: float = 0.1): return repositories.build_event_subscriber(self.db_path, poll_interval_seconds=poll_interval_seconds)
    def build_runtime_outbox_repository(self): return repositories.build_runtime_outbox_repository(self.db_path)
    def build_agent_repositories(self): return repositories.build_agent_repositories(self.db_path)
    def build_agent_document_repository(self): return repositories.build_agent_document_repository(self.db_path)
    def build_agent_evidence_repository(self): return repositories.build_agent_evidence_repository(self.db_path)
    def build_agent_run_queue(self): return repositories.build_agent_run_queue(self.db_path)
    def build_agent_idempotency_store(self): return repositories.build_agent_idempotency_store(self.db_path)
    def build_agent_unit_of_work(self, event_publisher: Any = None): return repositories.build_agent_unit_of_work(self.db_path, event_publisher=event_publisher)

    # -- Session use cases --
    def build_create_session_use_case(self): return use_cases.build_create_session_use_case(self.db_path)
    def build_resume_session_use_case(self): return use_cases.build_resume_session_use_case(self.db_path)
    def build_list_sessions_use_case(self): return use_cases.build_list_sessions_use_case(self.db_path)
    def build_append_turn_use_case(self): return use_cases.build_append_turn_use_case(self.db_path)

    # -- Runtime factories --
    def build_model_router(self, document_repository=None): return runtime_kernel.build_model_router(document_repository=document_repository)
    def build_agent_backends(self, secret_provider=None): return runtime_kernel.build_agent_backends(self.gateway_container, secret_provider)
    def build_agent_runtime_kernel(self, model=None, tool_registry=None, event_publisher=None): return runtime_kernel.build_agent_runtime_kernel(self.db_path, self.gateway_container, self.build_default_tool_registry, model=model, tool_registry=tool_registry, event_publisher=event_publisher)
    def build_research_agent_runtime(self, model: Any = None, tool_registry: Any = None): return runtime_kernel.build_research_agent_runtime(self.gateway_container, self.build_default_tool_registry, model=model, tool_registry=tool_registry)
    def build_persisted_research_agent_runtime(self, model: Any = None, tool_registry: Any = None, event_publisher: Any = None): return runtime_kernel.build_persisted_research_agent_runtime(self.db_path, self.gateway_container, self.build_default_tool_registry, model=model, tool_registry=tool_registry, event_publisher=event_publisher)

    # -- Agent-backed use cases and tools --
    def build_macro_strategist_agent_use_case(self, runtime=None): return agent_use_cases.build_macro_strategist_agent_use_case(self.build_persisted_research_agent_runtime, runtime)
    def build_industry_analyzer_agent_use_case(self, runtime=None): return agent_use_cases.build_industry_analyzer_agent_use_case(self.build_persisted_research_agent_runtime, runtime)
    def build_default_tool_registry(self, entitlement_checker: Any = None, context: Any = None): return tools.build_default_tool_registry(self.gateway_container, entitlement_checker=entitlement_checker, context=context)

    # -- Run/capability use cases --
    def build_run_summary_use_case(self, runtime: Any = None, evidence_repository: Any = None): return use_cases.build_run_summary_use_case(self.db_path, self.build_persisted_research_agent_runtime, runtime, evidence_repository)
    def build_capability_registry_use_case(self): return use_cases.build_capability_registry_use_case(self.build_default_tool_registry)
    def build_execute_run_use_case(self, model: Any = None, tool_registry: Any = None): return use_cases.build_execute_run_use_case(self.db_path, self.gateway_container, self.build_default_tool_registry, model=model, tool_registry=tool_registry)
    def build_resume_run_use_case(self, model: Any = None, tool_registry: Any = None): return use_cases.build_resume_run_use_case(self.db_path, self.gateway_container, self.build_default_tool_registry, model=model, tool_registry=tool_registry)
    def build_get_run_snapshot_use_case(self, model: Any = None, tool_registry: Any = None): return use_cases.build_get_run_snapshot_use_case(self.db_path, self.gateway_container, self.build_default_tool_registry, model=model, tool_registry=tool_registry)

    # -- Process graph collaborators --
    def gateway_container(self): return self._process_graph().gateway_container

    def _process_graph(self):
        if self.graph_provider is not None:
            return self.graph_provider()
        from doge.bootstrap.processes import build_embedded_process
        return build_embedded_process(db_path=self.db_path)


def build_runtime_container(db_path: Path | str | None = None) -> RuntimeContainer:
    """Build the runtime container."""
    from doge.bootstrap.processes import build_embedded_process
    return build_embedded_process(db_path=db_path).runtime_container
