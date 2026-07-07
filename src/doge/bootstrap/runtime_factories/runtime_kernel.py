"""Runtime factory helpers for research-agent runtime assembly."""

from __future__ import annotations

import os
from typing import Any

from doge.application.agent.approval_coordinator import ApprovalCoordinator
from doge.application.agent.artifact_citation_assembler import ArtifactCitationAssembler
from doge.application.agent.artifact_finalizer import ArtifactFinalizer
from doge.application.agent.context_builder import ContextBuilder
from doge.application.agent.model_response_assembler import ModelResponseAssembler
from doge.application.agent.model_router import ModelRouter
from doge.application.agent.run_lifecycle_service import RunLifecycleService
from doge.application.agent.run_stepper import RunStepper
from doge.application.agent.runtime_kernel import RuntimeKernel
from doge.application.agent.transition_recorder import TransitionRecorder
from doge.application.agent.web_search_stage import WebSearchStage
from doge.application.services.citation_support_classifier import CitationSupportClassifier
from doge.application.services.claim_validation_service import ClaimValidationService
from doge.application.services.citation_service import CitationService
from doge.config import get_settings
from doge.infrastructure.agent.backends import KimiAgentSdkBackend
from doge.infrastructure.agent.persisted_runtime import PersistedResearchAgentRuntime
from doge.platform.runtime.services import (
    ArtifactEvaluationService,
    ModelExecutionService,
    ToolExecutionService,
)
from doge.bootstrap.runtime_factories import repositories


def _demo_fallback_allowed() -> bool:
    """Whether the demo/test scripted-model fallback may be used.

    Allowed only in ``local_demo`` auth mode (the default loopback posture) or
    when explicitly opted in via ``DOGE_ALLOW_DEMO_RUNTIME=1``. Enterprise/remote
    production paths fail closed instead of silently using a scripted model.
    """
    if os.environ.get("DOGE_ALLOW_DEMO_RUNTIME", "").strip() == "1":
        return True
    return get_settings().auth.mode == "local_demo"


def build_model_router(document_repository=None) -> ModelRouter:
    return ModelRouter(document_repository=document_repository, settings=get_settings())


def build_agent_backends(gateway_container_fn, secret_provider=None):
    if get_settings().features.slot_platform:
        from doge.bootstrap.runtime_factories.slots import build_slot_aware_agent_backends

        return build_slot_aware_agent_backends(gateway_container_fn, secret_provider)
    settings = get_settings()
    secret_provider = secret_provider or gateway_container_fn().build_secret_provider()
    return {
        "kimi_agent_sdk": KimiAgentSdkBackend(
            base_url=settings.kimi.effective_base_url(),
            model=settings.kimi.general_model,
            secret_provider=secret_provider,
        )
    }


def build_agent_runtime_kernel(
    db_path,
    gateway_container_fn,
    default_tool_registry_fn,
    *,
    model=None,
    tool_registry=None,
    event_publisher=None,
) -> RuntimeKernel:
    repos = repositories.build_agent_repositories(db_path)
    gateway = gateway_container_fn()
    secret_provider = gateway.build_secret_provider()
    if model is None:
        if secret_provider.get_secret("kimi.api_key"):
            model = gateway.build_kimi_agent_model(secret_provider)
        elif _demo_fallback_allowed():
            from doge.infrastructure.agent.scripted_model import ScriptedAgentModel

            model = ScriptedAgentModel()
        else:
            raise RuntimeError(
                "no live model adapter configured and demo fallback is disabled "
                "(auth.mode is not local_demo). For local demo/test set "
                "DOGE_AUTH_MODE=local_demo or DOGE_ALLOW_DEMO_RUNTIME=1; otherwise "
                "configure a live model adapter (kimi.api_key)."
            )
    if tool_registry is None:
        tool_registry = default_tool_registry_fn()
    model_router = build_model_router(document_repository=repos["documents"])
    agent_backends = build_agent_backends(gateway_container_fn, secret_provider)
    response_assembler = ModelResponseAssembler()
    transition_recorder = TransitionRecorder(
        transaction_factory=repositories.build_runtime_transaction_factory(db_path),
        event_publisher=event_publisher,
    )
    artifact_finalizer = ArtifactFinalizer(evaluation_service=ArtifactEvaluationService())
    citation_assembler = ArtifactCitationAssembler(
        evidence_repository=repos["evidence"],
        citation_service=CitationService(),
        claim_validation_service=ClaimValidationService(),
        classifier=CitationSupportClassifier(),
    )
    stepper = RunStepper(
        run_repository=repos["runs"],
        event_repository=repos["events"],
        artifact_repository=repos["artifacts"],
        approval_repository=repos["approvals"],
        context_builder=ContextBuilder(
            document_repository=repos["documents"],
            evidence_repository=repos["evidence"],
            session_repository=repos["sessions"],
            run_repository=repos["runs"],
        ),
        response_assembler=response_assembler,
        model_execution_service=ModelExecutionService(
            model=model,
            response_assembler=response_assembler,
            model_router=model_router,
            web_search_stage=WebSearchStage(model, response_assembler=response_assembler),
            agent_backends=agent_backends,
        ),
        tool_execution_service=ToolExecutionService(
            tool_registry=tool_registry,
            governance_repository=repos["governance"],
        ),
        artifact_finalizer=artifact_finalizer,
        transition_recorder=transition_recorder,
        citation_assembler=citation_assembler,
    )
    lifecycle = RunLifecycleService(
        run_repository=repos["runs"],
        event_repository=repos["events"],
        artifact_repository=repos["artifacts"],
        approval_repository=repos["approvals"],
        transition_recorder=transition_recorder,
        run_stepper=stepper,
    )
    return RuntimeKernel(
        lifecycle_service=lifecycle,
        stepper=stepper,
        transition_recorder=transition_recorder,
        approval_coordinator=ApprovalCoordinator(
            run_repository=repos["runs"],
            approval_repository=repos["approvals"],
            transition_recorder=transition_recorder,
        ),
        artifact_finalizer=artifact_finalizer,
    )


def build_research_agent_runtime(gateway_container_fn, default_tool_registry_fn, *, model: Any = None, tool_registry: Any = None):
    if not _demo_fallback_allowed():
        raise RuntimeError(
            "InMemoryResearchAgentRuntime is a demo/test-only runtime; the current "
            "auth.mode is not local_demo. Use the persisted runtime with a live model "
            "adapter for non-demo paths, or set DOGE_AUTH_MODE=local_demo / "
            "DOGE_ALLOW_DEMO_RUNTIME=1 for local demo/test."
        )
    from doge.infrastructure.agent.inmemory_runtime import InMemoryResearchAgentRuntime
    from doge.infrastructure.agent.scripted_model import ScriptedAgentModel

    gateway = gateway_container_fn()
    secret_provider = gateway.build_secret_provider()
    if model is None:
        model = (
            gateway.build_kimi_agent_model(secret_provider)
            if secret_provider.get_secret("kimi.api_key")
            else ScriptedAgentModel()
        )
    if tool_registry is None:
        tool_registry = default_tool_registry_fn()
    return InMemoryResearchAgentRuntime(model=model, tool_registry=tool_registry)


def build_persisted_research_agent_runtime(
    db_path,
    gateway_container_fn,
    default_tool_registry_fn,
    *,
    model: Any = None,
    tool_registry: Any = None,
    event_publisher: Any = None,
) -> PersistedResearchAgentRuntime:
    return PersistedResearchAgentRuntime(
        build_agent_runtime_kernel(
            db_path,
            gateway_container_fn,
            default_tool_registry_fn,
            model=model,
            tool_registry=tool_registry,
            event_publisher=event_publisher,
        )
    )
