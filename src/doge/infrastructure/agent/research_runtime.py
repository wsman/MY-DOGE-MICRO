"""In-memory research-agent runtime adapter."""

from doge.application.agent.research_runtime import ResearchAgentRuntime
from doge.core.ports.agent_runtime import IResearchAgentRuntime


class InMemoryResearchAgentRuntime(ResearchAgentRuntime, IResearchAgentRuntime):
    """Concrete demo adapter for the research-agent runtime port.

    The state-machine implementation remains in the application layer. This
    adapter makes the chosen storage policy explicit: in-memory run state is
    acceptable for the interview demo and replaceable by a persisted runtime
    adapter in production.
    """
