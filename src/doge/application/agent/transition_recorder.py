"""Transition recording service for runtime state changes."""

from __future__ import annotations

from typing import Any

from doge.application.agent.state_machine import ensure_transition
from doge.core.domain.agent_models import AgentEvent, AgentRun, EventType, RunStatus, utc_now
from doge.core.ports.event_publisher import IEventPublisher
from doge.core.ports.runtime_transaction import IRuntimeTransactionFactory
from doge.shared.scope import TenantScope


class _NoopEventPublisher:
    async def publish(self, event: AgentEvent) -> None:
        return None


class TransitionRecorder:
    """Record run status transitions, events, artifacts, and approvals transactionally."""

    def __init__(
        self,
        *,
        transaction_factory: IRuntimeTransactionFactory,
        event_publisher: IEventPublisher | None = None,
    ) -> None:
        self._transactions = transaction_factory
        self._publisher = event_publisher or _NoopEventPublisher()

    async def record(
        self,
        run: AgentRun,
        *,
        status: RunStatus | None = None,
        events: list[tuple[EventType, dict[str, Any]]] | None = None,
        artifacts: list[Any] | None = None,
        approvals: list[Any] | None = None,
        save_run: bool = False,
    ) -> list[AgentEvent]:
        """Apply a state transition and persist it.

        Returns the persisted events so callers can await downstream effects.
        """
        if status is not None:
            ensure_transition(run.status, status)
            run.status = status
            run.updated_at = utc_now()
            save_run = True
        staged_events = [run.add_event(event_type, payload) for event_type, payload in (events or [])]
        tx = self._transactions.begin()
        persisted_events: list[AgentEvent] = []
        try:
            if save_run:
                tx.save_run(run)
            for event in staged_events:
                persisted_event = tx.append_event(event)
                tx.stage_outbox(persisted_event)
                persisted_events.append(persisted_event)
            for approval in approvals or []:
                tx.save_approval(approval)
            for artifact in artifacts or []:
                tx.save_artifact(artifact)
            tx.commit()
        except Exception:
            tx.rollback()
            raise
        for event in persisted_events:
            await self._publisher.publish(event)
        return persisted_events

    async def mark_cancelled(self, run: AgentRun) -> None:
        await self.record(
            run,
            status=RunStatus.CANCELLED,
            events=[(EventType.RUN_CANCELLED, {"cancelled": True})],
        )

    async def mark_failed(self, run: AgentRun, message: str, *, code: str = "runtime_failure") -> None:
        from doge.shared.errors import SafeError

        safe_error = SafeError.create(code, message)
        await self.record(
            run,
            status=RunStatus.FAILED,
            events=[(EventType.ERROR, {
                "message": safe_error.public_message,
                "error": safe_error.to_event_payload(),
            })],
        )

    @staticmethod
    def effective_tenant_id(run: AgentRun, tenant_id: str | None = None) -> str | None:
        if tenant_id is not None:
            return tenant_id
        if run.identity_snapshot is None:
            return None
        return run.identity_snapshot.tenant_id

    @staticmethod
    def noop_publisher() -> IEventPublisher:
        return _NoopEventPublisher()
