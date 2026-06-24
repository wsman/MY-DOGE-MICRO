from __future__ import annotations

import asyncio
from pathlib import Path
from typing import AsyncIterator

from doge.core.domain.agent_models import AgentEvent
from doge.core.ports.event_subscriber import IEventSubscriber
from doge.infrastructure.database.agent_repositories import SQLiteEventRepository


class SQLiteEventSubscriber(IEventSubscriber):
    def __init__(self, db_path: Path | str | None = None, *, poll_interval_seconds: float = 0.1) -> None:
        self._events = SQLiteEventRepository(db_path)
        self._poll_interval_seconds = poll_interval_seconds

    async def subscribe(self, run_id: str, after_sequence: int = 0) -> AsyncIterator[AgentEvent]:
        last_seen = after_sequence
        while True:
            events = self._events.list_for_run(run_id, after_sequence=last_seen)
            if events:
                for event in events:
                    last_seen = event.sequence
                    yield event
                continue
            await asyncio.sleep(self._poll_interval_seconds)
