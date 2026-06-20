"""Deprecated import path for the in-memory research-agent runtime."""

from __future__ import annotations

import warnings

from doge.infrastructure.agent.inmemory_runtime import InMemoryResearchAgentRuntime


warnings.warn(
    "doge.infrastructure.agent.research_runtime is deprecated; "
    "import InMemoryResearchAgentRuntime from doge.infrastructure.agent.inmemory_runtime.",
    DeprecationWarning,
    stacklevel=2,
)


__all__ = ["InMemoryResearchAgentRuntime"]
