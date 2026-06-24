from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator

from doge.core.domain.agent_models import AgentEvent


class IEventSubscriber(ABC):
    @abstractmethod
    async def subscribe(self, run_id: str, after_sequence: int = 0) -> AsyncIterator[AgentEvent]:
        ...
