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
from doge.shared.scope import TenantScope


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

    def save(
        self,
        run: AgentRun,
        scope: TenantScope | str | None = None,
        *,
        tenant_id: str | None = None,
    ) -> None:
        requested_tenant_id = _tenant_id_from_scope(scope, tenant_id)
        if requested_tenant_id is not None and not _matches_tenant(_tenant_id_from_run(run), requested_tenant_id):
            raise ValueError("tenant mismatch for run")
        stored = deepcopy(run)
        stored.events = []
        stored.artifacts = []
        stored.approvals = []
        self._store.runs[run.run_id] = stored

    def get(
        self,
        run_id: str,
        scope: TenantScope | str | None = None,
        *,
        tenant_id: str | None = None,
    ) -> AgentRun | None:
        requested_tenant_id = _tenant_id_from_scope(scope, tenant_id)
        run = self._store.runs.get(run_id)
        if run is None or not _matches_tenant(_tenant_id_from_run(run), requested_tenant_id):
            return None
        hydrated = deepcopy(run)
        hydrated.events = deepcopy(
            InMemoryEventRepository(self._store).list_for_run(run_id, tenant_id=requested_tenant_id)
        )
        hydrated.artifacts = deepcopy(
            InMemoryArtifactRepository(self._store).list_for_run(run_id, tenant_id=requested_tenant_id)
        )
        hydrated.approvals = [
            deepcopy(approval)
            for approval in InMemoryApprovalRepository(self._store).list_for_run(
                run_id,
                tenant_id=requested_tenant_id,
            )
        ]
        hydrated.approvals.sort(key=lambda item: item.created_at)
        return hydrated

    def get_run_header(
        self,
        run_id: str,
        scope: TenantScope | str | None = None,
        *,
        tenant_id: str | None = None,
    ) -> AgentRun | None:
        requested_tenant_id = _tenant_id_from_scope(scope, tenant_id)
        run = self._store.runs.get(run_id)
        if run is None or not _matches_tenant(_tenant_id_from_run(run), requested_tenant_id):
            return None
        header = deepcopy(run)
        header.events = []
        header.artifacts = []
        header.approvals = []
        return header

    def list_by_session(
        self,
        session_id: str,
        scope: TenantScope | str | None = None,
        *,
        tenant_id: str | None = None,
    ) -> list[AgentRun]:
        requested_tenant_id = _tenant_id_from_scope(scope, tenant_id)
        runs = [
            run for run in self._store.runs.values()
            if run.session_id == session_id and _matches_tenant(_tenant_id_from_run(run), requested_tenant_id)
        ]
        hydrated: list[AgentRun] = []
        for run in sorted(runs, key=lambda item: item.created_at):
            loaded = self.get(run.run_id, tenant_id=requested_tenant_id)
            if loaded is not None:
                hydrated.append(loaded)
        return hydrated

    def list_recent(
        self,
        scope: TenantScope | int | str | None = None,
        limit: int = 20,
        *,
        tenant_id: str | None = None,
    ) -> list[AgentRun]:
        if isinstance(scope, int):
            limit = scope
            scope = None
        requested_tenant_id = _tenant_id_from_scope(scope, tenant_id)
        runs = [
            run for run in self._store.runs.values()
            if _matches_tenant(_tenant_id_from_run(run), requested_tenant_id)
        ]
        runs = sorted(runs, key=lambda item: item.updated_at, reverse=True)[:limit]
        hydrated: list[AgentRun] = []
        for run in runs:
            loaded = self.get(run.run_id, tenant_id=requested_tenant_id)
            if loaded is not None:
                hydrated.append(loaded)
        return hydrated


class InMemoryEventRepository(IEventRepository):
    def __init__(self, store: _InMemoryAgentStore | None = None) -> None:
        self._store = store or _InMemoryAgentStore()

    def append(self, event: AgentEvent, tenant_id: str | None = None) -> AgentEvent:
        run = self._store.runs.get(event.run_id)
        if run is not None and not _matches_tenant(_tenant_id_from_run(run), tenant_id):
            raise PermissionError("event tenant mismatch")
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
        run = self._store.runs.get(run_id)
        if run is not None and not _matches_tenant(_tenant_id_from_run(run), tenant_id):
            return []
        return [
            deepcopy(event)
            for event in self._store.events.get(run_id, [])
            if event.sequence > after_sequence
        ]


class InMemoryArtifactRepository(IArtifactRepository):
    def __init__(self, store: _InMemoryAgentStore | None = None) -> None:
        self._store = store or _InMemoryAgentStore()

    def save(self, artifact: AgentArtifact, tenant_id: str | None = None) -> None:
        run = self._store.runs.get(artifact.run_id)
        if run is not None and not _matches_tenant(_tenant_id_from_run(run), tenant_id):
            raise PermissionError("artifact tenant mismatch")
        artifacts = [
            item
            for item in self._store.artifacts.get(artifact.run_id, [])
            if item.artifact_id != artifact.artifact_id
        ]
        artifacts.append(deepcopy(artifact))
        artifacts.sort(key=lambda item: item.created_at)
        self._store.artifacts[artifact.run_id] = artifacts

    def list_for_run(self, run_id: str, tenant_id: str | None = None) -> list[AgentArtifact]:
        run = self._store.runs.get(run_id)
        if run is not None and not _matches_tenant(_tenant_id_from_run(run), tenant_id):
            return []
        return deepcopy(self._store.artifacts.get(run_id, []))


class InMemoryApprovalRepository(IApprovalRepository):
    def __init__(self, store: _InMemoryAgentStore | None = None) -> None:
        self._store = store or _InMemoryAgentStore()

    def save(self, approval: AgentApproval, tenant_id: str | None = None) -> None:
        run = self._store.runs.get(approval.run_id)
        if run is not None and not _matches_tenant(_tenant_id_from_run(run), tenant_id):
            raise PermissionError("approval tenant mismatch")
        self._store.approvals[approval.approval_id] = deepcopy(approval)

    def get(self, approval_id: str, tenant_id: str | None = None) -> AgentApproval | None:
        approval = self._store.approvals.get(approval_id)
        if approval is not None:
            run = self._store.runs.get(approval.run_id)
            if run is not None and not _matches_tenant(_tenant_id_from_run(run), tenant_id):
                return None
        return deepcopy(approval) if approval is not None else None

    def list_for_run(self, run_id: str, tenant_id: str | None = None) -> list[AgentApproval]:
        run = self._store.runs.get(run_id)
        if run is not None and not _matches_tenant(_tenant_id_from_run(run), tenant_id):
            return []
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


def _tenant_id_from_run(run: AgentRun) -> str | None:
    if run.identity_snapshot is None:
        return None
    return run.identity_snapshot.tenant_id


def _matches_tenant(record_tenant_id: str | None, requested_tenant_id: str | None) -> bool:
    if requested_tenant_id is None:
        return True
    return (record_tenant_id or "local") == (requested_tenant_id or "local")


def _tenant_id_from_scope(scope: TenantScope | str | None, tenant_id: str | None = None) -> str | None:
    if isinstance(scope, TenantScope):
        if tenant_id is not None and tenant_id != scope.tenant_id:
            raise ValueError(f"tenant mismatch for scope: {tenant_id} != {scope.tenant_id}")
        return scope.tenant_id
    if isinstance(scope, str):
        if tenant_id is not None and tenant_id != scope:
            raise ValueError(f"tenant mismatch for scope: {tenant_id} != {scope}")
        return scope
    return tenant_id
