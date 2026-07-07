"""Agent Runtime facade.

Exports are lazy to avoid import cycles while RuntimeKernel is being migrated
into this target bounded-context package.
"""

from importlib import import_module
from typing import Any


_EXPORTS = {
    "AgentApproval": ("doge.core.domain.agent_models", "AgentApproval"),
    "AgentArtifact": ("doge.core.domain.agent_models", "AgentArtifact"),
    "AgentContentPart": ("doge.core.ports.agent_model", "AgentContentPart"),
    "AgentEvent": ("doge.core.domain.agent_models", "AgentEvent"),
    "AgentMessage": ("doge.core.ports.agent_model", "AgentMessage"),
    "AgentResponse": ("doge.core.ports.agent_model", "AgentResponse"),
    "AgentRun": ("doge.core.domain.agent_models", "AgentRun"),
    "AgentSession": ("doge.core.domain.agent_models", "AgentSession"),
    "AgentTurn": ("doge.core.domain.agent_models", "AgentTurn"),
    "ApprovalCoordinator": ("doge.application.agent.approval_coordinator", "ApprovalCoordinator"),
    "ArtifactEvaluationService": ("doge.platform.runtime.services", "ArtifactEvaluationService"),
    "ArtifactFinalizer": ("doge.application.agent.artifact_finalizer", "ArtifactFinalizer"),
    "AsyncioWorker": ("doge.application.agent.worker", "AsyncioWorker"),
    "Citation": ("doge.core.domain.agent_models", "Citation"),
    "ContextBuilder": ("doge.application.agent.context_builder", "ContextBuilder"),
    "EventBus": ("doge.application.agent.event_bus", "EventBus"),
    "EventType": ("doge.core.domain.agent_models", "EventType"),
    "ExecutionProfile": ("doge.core.domain.execution_profile", "ExecutionProfile"),
    "ExecutionProfileSpec": ("doge.core.domain.execution_profile", "ExecutionProfileSpec"),
    "IAgentBackend": ("doge.core.ports.agent_backend", "IAgentBackend"),
    "IAgentModel": ("doge.core.ports.agent_model", "IAgentModel"),
    "IApprovalRepository": ("doge.core.ports.agent_repository", "IApprovalRepository"),
    "IApprovalCoordinator": ("doge.core.ports.runtime_services", "IApprovalCoordinator"),
    "IArtifactEvaluationService": ("doge.core.ports.runtime_services", "IArtifactEvaluationService"),
    "IArtifactFinalizer": ("doge.core.ports.runtime_services", "IArtifactFinalizer"),
    "IArtifactRepository": ("doge.core.ports.agent_repository", "IArtifactRepository"),
    "IEventPublisher": ("doge.core.ports.event_publisher", "IEventPublisher"),
    "IEventRepository": ("doge.core.ports.agent_repository", "IEventRepository"),
    "IModelRouter": ("doge.core.ports.model_router", "IModelRouter"),
    "IModelExecutionService": ("doge.core.ports.runtime_services", "IModelExecutionService"),
    "IModelResponseAssembler": ("doge.core.ports.runtime_services", "IModelResponseAssembler"),
    "IResearchAgentRuntime": ("doge.core.ports.agent_runtime", "IResearchAgentRuntime"),
    "IRuntimeEventWatcher": ("doge.core.ports.runtime_services", "IRuntimeEventWatcher"),
    "IRunLifecycleService": ("doge.core.ports.runtime_services", "IRunLifecycleService"),
    "IRunQueue": ("doge.core.ports.worker_queue", "IRunQueue"),
    "IRunRepository": ("doge.core.ports.agent_repository", "IRunRepository"),
    "IRunStepper": ("doge.core.ports.runtime_services", "IRunStepper"),
    "ISessionRepository": ("doge.core.ports.agent_repository", "ISessionRepository"),
    "IToolExecutionService": ("doge.core.ports.runtime_services", "IToolExecutionService"),
    "ITransitionRecorder": ("doge.core.ports.runtime_services", "ITransitionRecorder"),
    "IWebSearchStage": ("doge.core.ports.runtime_services", "IWebSearchStage"),
    "InvalidRunStatusTransition": ("doge.application.agent.state_machine", "InvalidRunStatusTransition"),
    "ModelExecutionResult": ("doge.core.ports.runtime_services", "ModelExecutionResult"),
    "ModelExecutionService": ("doge.platform.runtime.services", "ModelExecutionService"),
    "ModelPolicy": ("doge.core.domain.model_policy", "ModelPolicy"),
    "ModelResponseAssembler": ("doge.application.agent.model_response_assembler", "ModelResponseAssembler"),
    "ModelRouter": ("doge.application.agent.model_router", "ModelRouter"),
    "OutboxPublisher": ("doge.application.agent.outbox_publisher", "OutboxPublisher"),
    "ProfileRegistry": ("doge.core.domain.execution_profile", "ProfileRegistry"),
    "RoutingDecision": ("doge.core.ports.model_router", "RoutingDecision"),
    "RunStatus": ("doge.core.domain.agent_models", "RunStatus"),
    "RunLifecycleService": ("doge.application.agent.run_lifecycle_service", "RunLifecycleService"),
    "RunStepper": ("doge.application.agent.run_stepper", "RunStepper"),
    "RuntimeEventWatcherMiddleware": ("doge.platform.runtime.watchers", "RuntimeEventWatcherMiddleware"),
    "RuntimeEventWatcherSlot": ("doge.platform.runtime.slot", "RuntimeEventWatcherSlot"),
    "RuntimeKernel": ("doge.application.agent.runtime_kernel", "RuntimeKernel"),
    "ToolApplicationService": ("doge.application.agent.tool_service", "ToolApplicationService"),
    "ToolExecutionProviderRegistry": ("doge.application.capabilities.registry", "ToolExecutionProviderRegistry"),
    "ToolExecutionService": ("doge.platform.runtime.services", "ToolExecutionService"),
    "ToolRegistry": ("doge.application.tools", "ToolRegistry"),
    "ToolResult": ("doge.core.ports.runtime_services", "ToolResult"),
    "TransitionRecorder": ("doge.application.agent.transition_recorder", "TransitionRecorder"),
    "WatcherDecisionError": ("doge.platform.runtime.watchers", "WatcherDecisionError"),
    "build_default_tool_registry": ("doge.application.tools", "build_default_tool_registry"),
    "can_transition": ("doge.application.agent.state_machine", "can_transition"),
    "ensure_transition": ("doge.application.agent.state_machine", "ensure_transition"),
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(name)
    module_name, attr_name = _EXPORTS[name]
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value
