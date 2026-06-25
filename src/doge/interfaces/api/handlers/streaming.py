"""Run streaming API handlers without FastAPI dependencies."""

from __future__ import annotations

from doge.core.domain.agent_models import RunStatus
from doge.interfaces.api.handlers.queries import GetRunHandler, RunAccessContext

STREAM_CLOSE_STATUSES = {
    RunStatus.AWAITING_APPROVAL,
    RunStatus.COMPLETED,
    RunStatus.FAILED,
    RunStatus.CANCELLED,
}
STREAM_CLOSE_EVENTS = {
    "approval_requested",
    "artifact_created",
    "error",
    "run_cancelled",
}


class RunStreamHandler:
    def __init__(self, *, runtime, subscriber) -> None:
        self._runtime = runtime
        self._subscriber = subscriber

    def open(self, *, run_id: str, access: RunAccessContext, after_sequence: int = 0):
        run = GetRunHandler(runtime=self._runtime).handle(run_id=run_id, access=access)
        terminal_at_start = run.status in STREAM_CLOSE_STATUSES
        initial_max_sequence = self._max_event_sequence_after(
            run_id,
            after_sequence,
            access=access,
        )
        return self._iter_events(
            run_id=run_id,
            access=access,
            after_sequence=after_sequence,
            terminal_at_start=terminal_at_start,
            initial_max_sequence=initial_max_sequence,
        )

    async def _iter_events(
        self,
        *,
        run_id: str,
        access: RunAccessContext,
        after_sequence: int,
        terminal_at_start: bool,
        initial_max_sequence: int,
    ):
        if terminal_at_start and initial_max_sequence <= after_sequence:
            return
        async for event in self._subscriber.subscribe(run_id, after_sequence=after_sequence):
            yield event
            run = self._runtime.get_run(access.scope, run_id)
            if run and run.status in STREAM_CLOSE_STATUSES:
                if terminal_at_start and event.sequence >= initial_max_sequence:
                    return
                if not terminal_at_start and event.event_type.value in STREAM_CLOSE_EVENTS:
                    return

    def _max_event_sequence_after(
        self,
        run_id: str,
        after_sequence: int,
        *,
        access: RunAccessContext,
    ) -> int:
        return max(
            (
                event.sequence
                for event in self._runtime.list_events(access.scope, run_id)
                if event.sequence > after_sequence
            ),
            default=after_sequence,
        )
