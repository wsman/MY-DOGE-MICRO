"""RuntimeKernel-backed in-memory research-agent runtime adapter."""

from __future__ import annotations

from doge.application.agent.runtime_kernel import RuntimeKernel
from doge.application.agent.tools import ToolRegistry
from doge.core.ports.agent_model import IAgentModel
from doge.infrastructure.agent.persisted_runtime import PersistedResearchAgentRuntime
from doge.infrastructure.agent.inmemory_repositories import build_inmemory_repositories


class InMemoryResearchAgentRuntime(PersistedResearchAgentRuntime):
    """Research runtime backed by RuntimeKernel and process-local repositories."""

    def __init__(self, model: IAgentModel, tool_registry: ToolRegistry) -> None:
        repos = build_inmemory_repositories()
        kernel = RuntimeKernel(
            model=model,
            tool_registry=tool_registry,
            run_repository=repos["runs"],
            event_repository=repos["events"],
            artifact_repository=repos["artifacts"],
            approval_repository=repos["approvals"],
        )
        super().__init__(kernel)
