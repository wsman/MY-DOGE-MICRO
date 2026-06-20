"""In-process event bus for live agent SSE streams."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import AsyncIterator

from doge.core.domain.agent_models import AgentEvent
from doge.core.ports.event_publisher import IEventPublisher


class EventBus(IEventPublisher):
    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[AgentEvent]]] = defaultdict(set)

    async def publish(self, event: AgentEvent) -> None:
        for queue in list(self._subscribers.get(event.run_id, set())):
            await queue.put(event)

    async def subscribe(self, run_id: str) -> AsyncIterator[AgentEvent]:
        queue: asyncio.Queue[AgentEvent] = asyncio.Queue()
        self._subscribers[run_id].add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._subscribers[run_id].discard(queue)
