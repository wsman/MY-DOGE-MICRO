from __future__ import annotations

import asyncio
from contextlib import suppress

from doge.core.ports.event_publisher import IEventPublisher
from doge.core.ports.runtime_transaction import IOutboxRepository


class OutboxPublisher:
    """Poll and publish committed runtime events from the transactional outbox."""

    def __init__(
        self,
        outbox: IOutboxRepository,
        publisher: IEventPublisher,
        *,
        worker_id: str = "outbox-publisher",
        batch_size: int = 50,
        lease_seconds: int = 30,
        poll_interval_seconds: float = 0.1,
    ) -> None:
        self._outbox = outbox
        self._publisher = publisher
        self._worker_id = worker_id
        self._batch_size = batch_size
        self._lease_seconds = lease_seconds
        self._poll_interval_seconds = poll_interval_seconds
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def publish_once(self) -> int:
        events = self._outbox.claim_pending(
            worker_id=self._worker_id,
            batch_size=self._batch_size,
            lease_seconds=self._lease_seconds,
        )
        published: list[str] = []
        for event in events:
            await self._publisher.publish(event)
            published.append(event.event_id)
        self._outbox.mark_published(published)
        return len(published)

    async def _run(self) -> None:
        while True:
            published = await self.publish_once()
            if published == 0:
                await asyncio.sleep(self._poll_interval_seconds)
