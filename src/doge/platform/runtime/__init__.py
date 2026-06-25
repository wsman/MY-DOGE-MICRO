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
    "ArtifactEvaluationService": ("doge.platform.runtime.services", "ArtifactEvaluationService"),
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
    "IArtifactRepository": ("doge.core.ports.agent_repository", "IArtifactRepository"),
    "IEventPublisher": ("doge.core.ports.event_publisher", "IEventPublisher"),
    "IEventRepository": ("doge.core.ports.agent_repository", "IEventRepository"),
    "IModelRouter": ("doge.core.ports.model_router", "IModelRouter"),
    "IResearchAgentRuntime": ("doge.core.ports.agent_runtime", "IResearchAgentRuntime"),
    "IRunQueue": ("doge.core.ports.worker_queue", "IRunQueue"),
    "IRunRepository": ("doge.core.ports.agent_repository", "IRunRepository"),
    "ISessionRepository": ("doge.core.ports.agent_repository", "ISessionRepository"),
    "InvalidRunStatusTransition": ("doge.application.agent.state_machine", "InvalidRunStatusTransition"),
    "ModelExecutionResult": ("doge.core.ports.runtime_services", "ModelExecutionResult"),
    "ModelExecutionService": ("doge.platform.runtime.services", "ModelExecutionService"),
    "ModelPolicy": ("doge.core.domain.model_policy", "ModelPolicy"),
    "ModelResponseAssembler": ("doge.application.agent.model_response_assembler", "ModelResponseAssembler"),
    "ModelRouter": ("doge.application.agent.model_router", "ModelRouter"),
    "ProfileRegistry": ("doge.core.domain.execution_profile", "ProfileRegistry"),
    "RoutingDecision": ("doge.core.ports.model_router", "RoutingDecision"),
    "RunStatus": ("doge.core.domain.agent_models", "RunStatus"),
    "RuntimeKernel": ("doge.application.agent.runtime_kernel", "RuntimeKernel"),
    "ToolApplicationService": ("doge.application.agent.tool_service", "ToolApplicationService"),
    "ToolExecutionProviderRegistry": ("doge.application.capabilities.registry", "ToolExecutionProviderRegistry"),
    "ToolExecutionService": ("doge.platform.runtime.services", "ToolExecutionService"),
    "ToolRegistry": ("doge.application.agent.tools", "ToolRegistry"),
    "ToolResult": ("doge.core.ports.runtime_services", "ToolResult"),
    "build_default_tool_registry": ("doge.application.agent.tools", "build_default_tool_registry"),
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
