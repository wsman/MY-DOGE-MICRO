"""In-memory repositories for RuntimeKernel-backed demo runs."""

from __future__ import annotations

from copy import deepcopy

from doge.core.domain.agent_models import AgentApproval, AgentArtifact, AgentEvent, AgentRun
from doge.core.ports.agent_repository import (
    IApprovalRepository,
    IArtifactRepository,
    IEventRepository,
    IRunRepository,
)


class _InMemoryAgentStore:
    def __init__(self) -> None:
        self.runs: dict[str, AgentRun] = {}
        self.events: dict[str, list[AgentEvent]] = {}
        self.artifacts: dict[str, list[AgentArtifact]] = {}
        self.approvals: dict[str, AgentApproval] = {}


class InMemoryRunRepository(IRunRepository):
    def __init__(self, store: _InMemoryAgentStore | None = None) -> None:
        self._store = store or _InMemoryAgentStore()

    @property
    def store(self) -> _InMemoryAgentStore:
        return self._store

    def save(self, run: AgentRun, tenant_id: str | None = None) -> None:
        stored = deepcopy(run)
        stored.events = []
        stored.artifacts = []
        stored.approvals = []
        self._store.runs[run.run_id] = stored

    def get(self, run_id: str, tenant_id: str | None = None) -> AgentRun | None:
        run = self._store.runs.get(run_id)
        if run is None:
            return None
        hydrated = deepcopy(run)
        hydrated.events = deepcopy(self._store.events.get(run_id, []))
        hydrated.artifacts = deepcopy(self._store.artifacts.get(run_id, []))
        hydrated.approvals = [
            deepcopy(approval)
            for approval in self._store.approvals.values()
            if approval.run_id == run_id
        ]
        hydrated.approvals.sort(key=lambda item: item.created_at)
        return hydrated

    def list_by_session(self, session_id: str, tenant_id: str | None = None) -> list[AgentRun]:
        runs = [run for run in self._store.runs.values() if run.session_id == session_id]
        hydrated: list[AgentRun] = []
        for run in sorted(runs, key=lambda item: item.created_at):
            loaded = self.get(run.run_id)
            if loaded is not None:
                hydrated.append(loaded)
        return hydrated

    def list_recent(self, limit: int = 20, tenant_id: str | None = None) -> list[AgentRun]:
        runs = sorted(self._store.runs.values(), key=lambda item: item.updated_at, reverse=True)[:limit]
        hydrated: list[AgentRun] = []
        for run in runs:
            loaded = self.get(run.run_id)
            if loaded is not None:
                hydrated.append(loaded)
        return hydrated


class InMemoryEventRepository(IEventRepository):
    def __init__(self, store: _InMemoryAgentStore | None = None) -> None:
        self._store = store or _InMemoryAgentStore()

    def append(self, event: AgentEvent, tenant_id: str | None = None) -> AgentEvent:
        events = self._store.events.setdefault(event.run_id, [])
        if event.sequence <= 0:
            event.sequence = max((item.sequence for item in events), default=0) + 1
        elif any(item.sequence == event.sequence for item in events):
            raise ValueError(f"duplicate event sequence for run {event.run_id}: {event.sequence}")
        events.append(deepcopy(event))
        events.sort(key=lambda item: item.sequence)
        self._store.events[event.run_id] = events
        return deepcopy(event)

    def list_for_run(
        self,
        run_id: str,
        after_sequence: int = 0,
        tenant_id: str | None = None,
    ) -> list[AgentEvent]:
        return [
            deepcopy(event)
            for event in self._store.events.get(run_id, [])
            if event.sequence > after_sequence
        ]


class InMemoryArtifactRepository(IArtifactRepository):
    def __init__(self, store: _InMemoryAgentStore | None = None) -> None:
        self._store = store or _InMemoryAgentStore()

    def save(self, artifact: AgentArtifact, tenant_id: str | None = None) -> None:
        artifacts = [
            item
            for item in self._store.artifacts.get(artifact.run_id, [])
            if item.artifact_id != artifact.artifact_id
        ]
        artifacts.append(deepcopy(artifact))
        artifacts.sort(key=lambda item: item.created_at)
        self._store.artifacts[artifact.run_id] = artifacts

    def list_for_run(self, run_id: str, tenant_id: str | None = None) -> list[AgentArtifact]:
        return deepcopy(self._store.artifacts.get(run_id, []))


class InMemoryApprovalRepository(IApprovalRepository):
    def __init__(self, store: _InMemoryAgentStore | None = None) -> None:
        self._store = store or _InMemoryAgentStore()

    def save(self, approval: AgentApproval, tenant_id: str | None = None) -> None:
        self._store.approvals[approval.approval_id] = deepcopy(approval)

    def get(self, approval_id: str, tenant_id: str | None = None) -> AgentApproval | None:
        approval = self._store.approvals.get(approval_id)
        return deepcopy(approval) if approval is not None else None

    def list_for_run(self, run_id: str, tenant_id: str | None = None) -> list[AgentApproval]:
        approvals = [item for item in self._store.approvals.values() if item.run_id == run_id]
        approvals.sort(key=lambda item: item.created_at)
        return deepcopy(approvals)


def build_inmemory_repositories() -> dict[str, object]:
    store = _InMemoryAgentStore()
    return {
        "runs": InMemoryRunRepository(store),
        "events": InMemoryEventRepository(store),
        "artifacts": InMemoryArtifactRepository(store),
        "approvals": InMemoryApprovalRepository(store),
    }
