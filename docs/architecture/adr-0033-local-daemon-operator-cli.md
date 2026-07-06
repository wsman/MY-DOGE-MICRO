# ADR-0033: Local Daemon Operator CLI

## Status

Accepted

## Date

2026-07-05

## Decision Makers

wsman (product owner) · Codex implementation agent

## Summary

Sprint 024 implements the daemon operator panel items from
`C:\Users\WSMAN\.claude\plans\agent-quizzical-wolf.md` as local `doged` CLI
commands. The CLI remains operator-only and does not add new `/v1` routes or
SDK surfaces.

The key decision is to keep `doged runs`, `doged queue`, `doged features`, and
`doged routes` as local read-only inspection commands. `doged doctor` continues
to use `/health/ready` because that endpoint already represents the running
daemon's readiness state.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python >=3.10; FastAPI 0.123.8; SQLite local agent DB |
| **Domain** | CLI / Daemon operations / Local observability |
| **Knowledge Risk** | LOW — uses existing argparse CLI, existing SQLite repositories, existing FastAPI app route metadata, and existing readiness endpoint |
| **References Consulted** | `docs/reference/python/VERSION.md`, `standards/technical-preferences.md`, `docs/registry/architecture.yaml`, `design/cdd/bc-06-agent-runtime.md`, `design/cdd/bc-08-governance-evaluation.md`, `src/doge/interfaces/daemon/main.py`, `src/doge/infrastructure/database/readiness.py`, `src/doge/infrastructure/database/agent_repositories.py`, `C:\Users\WSMAN\.claude\plans\agent-quizzical-wolf.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | Focused doged CLI tests, queue repository tests, import-boundary validation, docs/maturity validators, plan closure gate |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0024 (Single Stack Runtime Direction), ADR-0025 (Streaming Semantics) |
| **Enables** | Sprint 024 daemon operator panel |
| **Blocks** | Future remote/operator HTTP admin API until an explicit `/v1/operator` contract ADR exists |
| **Ordering Note** | This ADR intentionally avoids public API expansion; remote operator panels remain a separate design. |

## Context

### Problem Statement

The daemon has readiness checks, worker metrics, feature flags, route metadata,
persisted runs, and a durable queue, but the `doged` CLI exposes only
`serve`, `status`, and basic `doctor`. Operators need a small local inspection
surface for routine debugging without opening the database manually.

### Constraints

- Preserve explicit maturity posture: `production_ready: false`,
  `stable_declaration: forbidden`, and Level 3 `experimental`.
- Keep all new commands read-only.
- Do not add `/v1` routes, SDK methods, SDK types, or SDK parity entries.
- Do not expose secrets or raw auth material.
- Keep daemon readiness sourced from the running daemon through `/health/ready`.
- Keep run and queue inspection local-first and bounded by explicit limits.

### Requirements

- `doged doctor --verbose` shows nested readiness details.
- `doged runs --recent [--limit N] [--json]` lists persisted recent runs.
- `doged queue --status [--json]` shows latest queue status counts.
- `doged features [--json]` lists feature flag values and lifecycle env vars.
- `doged routes [--json]` lists registered API route methods, paths, and names.
- Durable queue status counts must follow latest-status semantics.

## Decision

Use a local-read model for operator CLI commands:

```text
doged doctor --verbose
  -> HTTP GET /health/ready
  -> nested readiness printout

doged runs --recent
  -> local runtime repository composition
  -> SQLiteRunRepository.list_recent(TenantScope.local(), limit)

doged queue --status
  -> local runtime queue composition
  -> IRunQueue.status_summary()

doged features
  -> Settings.features + FEATURE_LIFECYCLES

doged routes
  -> FastAPI app.routes metadata
```

### Key Interfaces

`IRunQueue` gains one read-only method:

```python
def status_summary(self) -> dict[str, int]:
    """Return counts by latest queue status."""
```

`doged` gains operator commands:

```bash
doged doctor --verbose [--json] [--port N]
doged runs --recent [--limit N] [--json]
doged queue --status [--json]
doged features [--json]
doged routes [--json]
```

## Alternatives Considered

### Alternative 1: Add `/v1/operator/*` routes

- **Description**: Expose recent runs, queue status, feature flags, and route
  listings over HTTP.
- **Pros**: Keeps CLI stateless and reflects the running daemon exactly.
- **Cons**: Expands public route surface, docs/API route coverage, auth review,
  and SDK parity decisions.
- **Rejection Reason**: Sprint 024 is local operator tooling; public admin API
  design should be a separate ADR.

### Alternative 2: Direct SQLite and local app inspection

- **Description**: Use local repositories/settings/app metadata from `doged`.
- **Pros**: No public API expansion; simple, fast, and local-first.
- **Cons**: CLI reads local state directly for runs/queue/features/routes.
- **Rejection Reason**: Chosen for this sprint.

### Alternative 3: Only enhance `doctor`

- **Description**: Add `--verbose` to readiness and defer runs/queue/features/routes.
- **Pros**: Lowest risk.
- **Cons**: Leaves most Sprint 024 operator panel items incomplete.
- **Rejection Reason**: Insufficient for the approved roadmap.

## Consequences

### Positive

- Operators get immediate local visibility into daemon state without new API
  contracts.
- Queue status is now available through a port method instead of ad hoc SQL in
  CLI code.
- Existing route and feature metadata become inspectable from `doged`.

### Negative

- `doged` now imports local composition roots for read-only inspection.
- Remote/non-local operator panels still need a future API contract.
- Route listing reflects local app construction, not a remote daemon instance.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| CLI direct reads drift from running daemon | MEDIUM | LOW | Keep `doctor` HTTP-based; document route/features/runs/queue as local operator reads. |
| Queue summary semantics diverge from readiness | LOW | LOW | Use same latest-status grouping pattern and focused repository tests. |
| Route listing expands user-facing claims | LOW | MEDIUM | Treat command as local diagnostic only; no docs/API public route contract change. |

## CDD Requirements Addressed

| CDD Document | Requirement | How This ADR Addresses It |
|--------------|-------------|----------------------------|
| `design/cdd/bc-06-agent-runtime.md` | Operators can start, observe, cancel, and inspect agent runs with predictable state transitions. | Adds recent-run and queue-status CLI inspection. |
| `design/cdd/bc-08-governance-evaluation.md` | Governance and maturity state must stay explicit. | Feature command exposes feature lifecycle metadata without promoting maturity. |
| `design/cdd/product-concept.md` | Operator Control: long-running scans and model calls should be visible and recoverable. | Adds daemon readiness verbosity plus runs/queue inspection. |

## Performance Implications

- **CPU**: Small bounded SQLite reads and route metadata iteration.
- **Memory**: Bounded by `--limit` for recent runs.
- **Load Time**: CLI commands import the local app/container when needed.
- **Network**: Only `doctor` uses loopback HTTP readiness as before.

## Migration Plan

1. Add `IRunQueue.status_summary()` and implement it in `SQLiteRunQueue`.
2. Extend `doged` parser and command dispatch.
3. Add text and JSON output helpers for recent runs, queue, features, and routes.
4. Extend focused CLI/repository tests.
5. Record Sprint 024 CDD, sprint record, and evidence manifest.

## Validation Criteria

- `doged doctor --verbose` prints nested readiness fields.
- `doged runs --recent` prints recent run id/status/workflow/question and JSON
  output when requested.
- `doged queue --status` prints latest-status counts.
- `doged features` prints feature flag values and lifecycle env vars.
- `doged routes` prints method/path/name rows.
- `SQLiteRunQueue.status_summary()` follows latest-status semantics.
- Focused tests and governance validators pass.

## Related Decisions

- ADR-0024: Single Stack Runtime Direction
- ADR-0025: Streaming Semantics
- ADR-0032: Workspace Mode and Memo Export
