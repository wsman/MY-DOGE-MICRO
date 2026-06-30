"""Runtime factory helpers for session/run/capability use cases."""

from __future__ import annotations

from doge.application.capabilities.registry import (
    ApiCapabilityProvider,
    FeatureCapabilityProvider,
    MaturityCapabilityProvider,
    ModelProviderCapabilityProvider,
    ToolRegistryCapabilityProvider,
)
from doge.application.use_cases.capability_registry import BuildCapabilityRegistry
from doge.application.use_cases.run_summary import BuildRunSummary
from doge.application.use_cases.run_use_cases import ExecuteRun, GetRunSnapshot, ResumeRun
from doge.application.use_cases.session_use_cases import AppendTurn, CreateSession, ListSessions, ResumeSession
from doge.config import get_settings
from doge.infrastructure.database.agent_repositories import SQLiteSessionRepository
from doge.bootstrap.runtime_factories import repositories
from doge.bootstrap.runtime_factories import runtime_kernel


def build_create_session_use_case(db_path) -> CreateSession:
    return CreateSession(SQLiteSessionRepository(db_path))


def build_resume_session_use_case(db_path) -> ResumeSession:
    return ResumeSession(SQLiteSessionRepository(db_path))


def build_list_sessions_use_case(db_path) -> ListSessions:
    return ListSessions(SQLiteSessionRepository(db_path))


def build_append_turn_use_case(db_path) -> AppendTurn:
    return AppendTurn(SQLiteSessionRepository(db_path))


def build_run_summary_use_case(db_path, persisted_runtime_fn, runtime=None, evidence_repository=None) -> BuildRunSummary:
    if runtime is None:
        runtime = persisted_runtime_fn()
    if evidence_repository is None:
        evidence_repository = repositories.build_agent_evidence_repository(db_path)
    return BuildRunSummary(runtime, evidence_repository)


def build_capability_registry_use_case(default_tool_registry_fn) -> BuildCapabilityRegistry:
    settings = get_settings()
    return BuildCapabilityRegistry(
        settings,
        providers=[
            FeatureCapabilityProvider(settings),
            ModelProviderCapabilityProvider(settings),
            ApiCapabilityProvider(settings),
            MaturityCapabilityProvider(settings.project_root / "docs" / "progress" / "runtime-maturity.yaml"),
            ToolRegistryCapabilityProvider(default_tool_registry_fn()),
        ],
    )


def build_execute_run_use_case(db_path, gateway_container_fn, default_tool_registry_fn, *, model=None, tool_registry=None) -> ExecuteRun:
    runtime = runtime_kernel.build_persisted_research_agent_runtime(
        db_path,
        gateway_container_fn,
        default_tool_registry_fn,
        model=model,
        tool_registry=tool_registry,
    )
    return ExecuteRun(runtime, SQLiteSessionRepository(db_path))


def build_resume_run_use_case(db_path, gateway_container_fn, default_tool_registry_fn, *, model=None, tool_registry=None) -> ResumeRun:
    runtime = runtime_kernel.build_persisted_research_agent_runtime(
        db_path,
        gateway_container_fn,
        default_tool_registry_fn,
        model=model,
        tool_registry=tool_registry,
    )
    return ResumeRun(runtime)


def build_get_run_snapshot_use_case(db_path, gateway_container_fn, default_tool_registry_fn, *, model=None, tool_registry=None) -> GetRunSnapshot:
    runtime = runtime_kernel.build_persisted_research_agent_runtime(
        db_path,
        gateway_container_fn,
        default_tool_registry_fn,
        model=model,
        tool_registry=tool_registry,
    )
    return GetRunSnapshot(runtime)
