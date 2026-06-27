# ADR-0025: Runtime Streaming Semantics

## Status

Accepted

## Date

2026-06-27

## Last Verified

2026-06-27

## Decision Makers

Codex implementation agent; project owner approval via
`C:\Users\WSMAN\.claude\plans\my-doge-micro-hidden-tide.md`.

## Summary

MY-DOGE-MICRO distinguishes three runtime streaming concepts:
``IResearchAgentRuntime.list_events`` is a synchronous persisted-event query;
``IResearchAgentRuntime.stream_events`` is a replay-only async iterator over
already-persisted events; and live cross-process SSE streaming is provided by
``RunStreamHandler`` using ``IEventSubscriber.subscribe``. This removes the
previous semantic split where consumers could mistake the replay-only runtime
method for a live stream.

## Engine Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python >=3.10, FastAPI, sse-starlette, SQLite |
| **Domain** | Runtime, API, event streaming |
| **Knowledge Risk** | LOW |
| **References Consulted** | `src/doge/core/ports/agent_runtime.py`, `src/doge/core/ports/event_subscriber.py`, `src/doge/infrastructure/agent/persisted_runtime.py`, `src/doge/infrastructure/database/event_subscriber.py`, `src/doge/interfaces/api/routers/v1/run_stream.py`, `src/doge/interfaces/api/handlers/streaming.py` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | `tests/unit/architecture/test_streaming_semantics.py`, `tests/unit/interfaces/api/test_run_stream_handler.py`, `tests/integration/test_agent_sse_stream.py` |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0024 |
| **Enables** | Consistent SDK/Web streaming behavior, future outbox publisher activation |
| **Blocks** | None |
| **Ordering Note** | Should be implemented before any new streaming consumer is added. |

## Context

### Problem Statement

The runtime port exposed both ``list_events`` and ``stream_events``. The
persisted adapter implemented ``stream_events`` as a replay-only iterator over
events already in the database. Meanwhile, the canonical ``/v1/runs/{run_id}/stream``
SSE route used ``RunStreamHandler``, which combined historical replay via
``runtime.list_events`` with live events via ``IEventSubscriber.subscribe``.

This created a semantic split: ``runtime.stream_events`` looked like it should
provide live streaming, but it did not. New consumers could pick the wrong
method and miss events generated after the iterator started.

### Current State

- ``IResearchAgentRuntime.list_events(scope, run_id)`` returns a list.
- ``IResearchAgentRuntime.stream_events(scope, run_id)`` yields the same list asynchronously.
- ``/v1/runs/{run_id}/stream`` uses ``RunStreamHandler`` with ``IEventSubscriber.subscribe``.
- Legacy ``/api/runs/{run_id}/stream`` uses ``runtime.stream_events`` directly and is replay-only.
- The transactional outbox publisher is gated behind a feature flag that is off by default.

### Constraints

- Preserve backward compatibility for legacy ``/api/*`` routes and existing SDK clients.
- Do not introduce a second live-streaming abstraction on the runtime port.
- Keep the event subscriber port as the single extension point for cross-process delivery.

### Requirements

- The runtime port must clearly document replay-only semantics for ``stream_events``.
- The v1 SSE route must remain the canonical live stream endpoint.
- Tests must enforce that v1 streaming uses ``RunStreamHandler`` and ``IEventSubscriber``.

## Decision

### 1. Runtime Port Semantics

- ``list_events(scope, run_id)`` is a synchronous query for persisted events.
- ``stream_events(scope, run_id)`` is a replay-only async iterator over already-persisted events.
- Live streaming is not a runtime-port responsibility.

### 2. Live SSE Implementation

The canonical live SSE endpoint is ``/v1/runs/{run_id}/stream``. It uses
``RunStreamHandler``, which:

1. Loads the run header to determine terminal status.
2. Computes the maximum persisted-event sequence after ``Last-Event-ID``.
3. Subscribes to new events via ``IEventSubscriber.subscribe(run_id, after_sequence=...)``.
4. Closes the stream when the run reaches a terminal status or a terminal event is seen.

### 3. Legacy Compatibility

The legacy ``/api/runs/{run_id}/stream`` route remains replay-only and documents
itself as a compatibility surface. New clients must use ``/v1/runs/{run_id}/stream``.

### 4. Outbox Publisher

The transactional outbox publisher remains feature-flagged off. The staging
logic is preserved in the runtime transaction implementation so it can be
activated once the cross-process subscriber coverage is proven.

### Architecture

```text
Client
  |
  | GET /v1/runs/{run_id}/stream
  v
RunStreamHandler
  |-- runtime.list_events(scope, run_id)  [historical boundary]
  |-- subscriber.subscribe(run_id, after_sequence)  [live events]
  v
IEventSubscriber (SQLite polling / future outbox / bus)
```

### Key Interfaces

```python
class IResearchAgentRuntime(ABC):
    def list_events(self, scope: TenantScope, run_id: str) -> list[AgentEvent]: ...
    async def stream_events(self, scope: TenantScope, run_id: str) -> AsyncIterator[AgentEvent]:
        """Replay-only iterator over already-persisted events."""

class IEventSubscriber(ABC):
    async def subscribe(self, run_id: str, after_sequence: int = 0) -> AsyncIterator[AgentEvent]: ...
```

### Implementation Guidelines

- Do not add live semantics to ``IResearchAgentRuntime.stream_events``.
- Do not call ``runtime.stream_events`` from the v1 SSE route.
- Document any new streaming route's contract as replay vs live explicitly.

## Alternatives Considered

### Alternative 1: Make ``stream_events`` live

- **Description**: Inject ``IEventSubscriber`` into the persisted runtime so ``stream_events`` becomes live.
- **Pros**: Single method for consumers.
- **Cons**: Blurs the boundary between runtime state and transport; the port would depend on subscriber infrastructure.
- **Rejection Reason**: Keeps runtime port focused on state; live delivery is a transport concern.

### Alternative 2: Remove ``stream_events`` from the port

- **Description**: Delete the method entirely.
- **Pros**: Eliminates confusion.
- **Cons**: Breaks legacy ``/api/*`` route and any external consumer using it.
- **Rejection Reason**: Backward compatibility required until legacy route is removed.

## Consequences

### Positive

- Clear separation between persisted query, replay iterator, and live stream.
- v1 SSE route is the single source of truth for live events.
- Future outbox publisher activation does not change the runtime port.

### Negative

- ``stream_events`` remains a potentially misleading name; mitigated by docstrings and architecture tests.
- Legacy route must be maintained until its removal gate closes.

### Neutral

- ``IEventSubscriber`` implementations remain pluggable (SQLite polling today, bus/outbox tomorrow).

## Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| Consumer confuses replay and live | MEDIUM | MEDIUM | Architecture tests enforce v1 route uses subscriber; docstrings warn on ``stream_events``. |
| SQLite polling subscriber does not scale | MEDIUM | LOW | Subscriber is an adapter; can be replaced with bus/outbox without changing handlers. |

## Performance Implications

| Metric | Before | Expected After | Budget |
|--------|--------|---------------|--------|
| SSE latency | SQLite polling at 100ms | Same | < 1s per event |
| Memory | O(events in flight) | Same | Bounded by subscriber buffer |

## Migration Plan

1. Update docstrings on runtime port and persisted adapter.
2. Document v1 route as canonical live stream and legacy route as replay-only.
3. Add architecture tests and handler unit tests.
4. When outbox publisher feature flag is enabled, verify subscriber still delivers events correctly.

**Rollback plan**: Revert docstrings and tests; no production behavior changes.

## Validation Criteria

- [x] ``tests/unit/architecture/test_streaming_semantics.py`` passes.
- [x] ``tests/unit/interfaces/api/test_run_stream_handler.py`` passes.
- [x] ``tests/integration/test_agent_sse_stream.py`` passes.
- [ ] Outbox publisher live smoke passes when feature flag is enabled (external gate).

## CDD Requirements Addressed

Foundational — no direct CDD requirement. Enables: research-agent run streaming contract, SDK/Web event consumption, and future multi-process daemon deployment.

## Related

- ADR-0024: Single-Stack Runtime Direction
- `src/doge/core/ports/agent_runtime.py`
- `src/doge/core/ports/event_subscriber.py`
- `src/doge/interfaces/api/routers/v1/run_stream.py`
- `src/doge/interfaces/api/handlers/streaming.py`
- `src/doge/application/agent/outbox_publisher.py`
