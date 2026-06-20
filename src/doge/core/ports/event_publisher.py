"""Event publisher port for decoupling runtime persistence from live streams."""

from __future__ import annotations

from abc import ABC, abstractmethod

from doge.core.domain.agent_models import AgentEvent


class IEventPublisher(ABC):
    @abstractmethod
    async def publish(self, event: AgentEvent) -> None:
        ...
