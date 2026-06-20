"""Infrastructure event publisher adapters."""

from __future__ import annotations

from doge.core.domain.agent_models import AgentEvent
from doge.core.ports.event_publisher import IEventPublisher


class NullEventPublisher(IEventPublisher):
    async def publish(self, event: AgentEvent) -> None:
        return None
