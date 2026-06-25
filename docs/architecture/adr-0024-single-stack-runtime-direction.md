# ADR-0024: Single-Stack Runtime Direction

## Status
Accepted

## Date
2026-06-25

## Last Verified
2026-06-25

## Decision Makers
Codex implementation agent; project owner approval via
`C:\Users\Aby\.claude\plans\my-doge-micro-2026-06-25-github-scalable-planet.md`.

## Summary

MY-DOGE-MICRO will stop treating the legacy local product API, the old
application composition module, the in-memory agent demo, and the PyQt desktop
dashboard as parallel platform stacks. New platform work must use the persisted
runtime, process roots, `/v1` HTTP routes, and SDK clients. Legacy surfaces stay
available only as compatibility or demo entrypoints until their documented
removal gates close.

This decision does not promote the product maturity posture. Runtime maturity
remains:

- `production_ready: false`
- `stable_declaration: forbidden`
- Level 3 SDK/platform: `experimental`

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python >=3.10, FastAPI, SQLite, CLI/SDK clients, optional PyQt6 |
| **Domain** | Runtime, API, CLI, compatibility migration |
| **Knowledge Risk** | LOW; this records local architecture direction and deprecation rules |
| **References Consulted** | ADR-0001, ADR-0007, ADR-0011, ADR-0021, ADR-0022, `docs/progress/runtime-maturity.yaml`, `src/doge/bootstrap/processes.py`, `src/doge/interfaces/api/main.py`, `src/doge/application/composition.py`, `src/doge/infrastructure/agent/inmemory_runtime.py`, `src/interface/dashboard.py` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | Compatibility tests, docs validators, route/deprecation header tests |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0001, ADR-0007, ADR-0011, ADR-0021, ADR-0022 |
| **Enables** | Gate 7 single-stack closure, legacy API removal planning, process-root migration |
| **Blocks** | New platform features under legacy `/api/*`, new internal imports of `doge.application.composition`, production-facing in-memory runtime use |
| **Ordering Note** | Compatibility surfaces remain until replacement parity and removal gates are proven. |

## Context

The project has accumulated several valid but overlapping execution paths:

- Legacy local product routes under `/api/*`.
- Preferred daemon/platform routes under `/v1/*`.
- Historical composition factories under `doge.application.composition`.
- Process roots under `doge.bootstrap.processes`.
- In-memory Research Copilot runtime for demo and tests.
- Persisted runtime repositories and daemon worker for local Alpha operation.
- PyQt desktop dashboard as a local GUI surface.

Keeping these paths semantically equal would recreate a dual architecture. It
would also make future SDK, tenant, persistence, and API contract work harder
to reason about. Gate 7 therefore needs an explicit single-stack decision.

## Decision

### 1. Preferred Stack For New Platform Work

New platform/runtime work must use:

- Process roots from `doge.bootstrap.processes`.
- Persisted runtime repositories and durable queue paths.
- `/v1/*` FastAPI routes for HTTP contracts.
- Python and TypeScript SDK clients for daemon/gateway consumers.
- Server-side capability, maturity, ACL, and audit decisions.

### 2. Legacy `/api/*` Routes

Legacy `/api/*` routes remain mounted only for local loopback demo mode. They
are compatibility routes for market scans, data browsing, notes, macro/report
reads, config, the old agent demo, and document payload registration.

Rules:

- No new platform feature may be introduced only under `/api/*`.
- New integrations should use `/v1/*` or the SDK.
- Legacy routes must emit deprecation metadata headers:
  - `Deprecation: true`
  - `Sunset: Wed, 30 Sep 2026 00:00:00 GMT`
  - `Link: <...adr-0024-single-stack-runtime-direction.md>; rel="deprecation"`
- Removal is not allowed before 2026-09-30 and not before route parity,
  operator migration notes, compatibility tests, and a follow-up removal story
  are approved.

### 3. `doge.application.composition`

`doge.application.composition` remains a compatibility shim for old import
paths and brownfield use-case factories. Internal runtime/platform wiring
should migrate to process roots and bounded-context containers.

Rules:

- New internal code should import process roots from `doge.bootstrap.processes`.
- Compatibility imports may remain where tests or old entrypoints prove they
  are intentionally supported.
- The shim can be removed only after replacement imports, compatibility tests,
  and user migration notes exist.

### 4. In-Memory Runtime

`InMemoryResearchAgentRuntime` is demo/test-only. It is useful for zero-key
local demonstrations, deterministic unit tests, and isolated fixtures, but it
is not the production-facing runtime path.

Rules:

- HTTP daemon, SDK, and platform flows should prefer persisted runtime state.
- Runtime maturity docs must distinguish persisted runtime capability from
  in-memory demo support.
- Any new in-memory usage must name itself as demo/test compatibility.

### 5. PyQt Desktop Dashboard

The PyQt dashboard is a legacy-maintained local desktop surface. It may stay
usable through smoke tests and optional `[gui]` installation, but it is not the
preferred platform UI and does not imply production readiness.

Rules:

- New platform UX should use Web/SDK/v1 surfaces unless a separate PyQt story
  is approved.
- PyQt docs must mention the known Qt DLL portability blocker.
- PyQt support status can be changed only with an explicit removal/support
  policy and passing or intentionally retired smoke tests.

## Alternatives Considered

### Alternative 1: Keep `/api/*` and `/v1/*` as equal platforms

- **Pros**: avoids migration pressure.
- **Cons**: doubles contract surface, splits SDK parity, and hides tenant and
  persistence differences.
- **Rejection Reason**: creates permanent dual architecture.

### Alternative 2: Remove legacy routes and shims immediately

- **Pros**: fastest conceptual cleanup.
- **Cons**: breaks existing local workflows and route-coverage tests.
- **Rejection Reason**: brownfield compatibility requires a staged removal.

### Alternative 3: Single-stack direction with compatibility windows

- **Pros**: makes the preferred path unambiguous while preserving current local
  workflows.
- **Cons**: requires active deprecation tracking.
- **Rejection Reason**: chosen.

## Consequences

### Positive

- New work has one target platform path: process roots -> persisted runtime ->
  `/v1` -> SDK/Web/CLI clients.
- Compatibility surfaces are still testable and documented.
- Runtime maturity language can stay honest about demo-only paths.

### Negative

- Compatibility code remains for at least one deprecation window.
- `/api/*` docs and tests must keep route parity until removal.
- Developers must avoid adding convenience features to old surfaces.

### Neutral

- This ADR does not change external production gates.
- It does not change the current route count by itself.
- It does not require physical source moves beyond story-gated changes.

## Migration Plan

1. Add runtime deprecation headers to `/api/*` responses.
2. Update API, CLI, getting-started, runtime maturity, registry, and traceability
   docs to mark the preferred stack.
3. Keep compatibility tests for `/api/*`, deprecated entrypoints, and PyQt
   smoke while those surfaces remain.
4. Migrate remaining internal callers away from `doge.application.composition`
   in small stories.
5. Replace production-facing in-memory runtime paths with persisted runtime
   paths; retain in-memory only for demo/tests.
6. Before removing any compatibility surface, create a removal story that names
   replacement commands, migration notes, route/import parity evidence, and
   rollback plan.

## Validation Criteria

- `/api/*` responses include the deprecation metadata headers.
- Architecture registry includes ADR-0024.
- Architecture traceability and overview include ADR-0024.
- Runtime maturity docs distinguish preferred persisted runtime from
  demo/test-only in-memory runtime.
- User-facing docs do not imply PyQt production readiness.
- No production posture values are changed.

## CDD Requirements Addressed

| CDD System | Requirement | How This ADR Addresses It |
|------------|-------------|--------------------------|
| `bc-06-agent-runtime.md` | Runtime state and daemon execution should have a durable preferred path. | Makes persisted runtime the preferred platform path and limits in-memory use to demo/tests. |
| `sdk-daemon-client-interfaces.md` | SDK/daemon contracts need one authoritative runtime surface. | Makes `/v1` and SDK clients the target for new platform work. |
| `clean-architecture-migration.md` | Brownfield compatibility must be staged and test-backed. | Keeps shims with deprecation headers, tests, and removal gates. |
| `fastapi-service.md` | Local API compatibility must preserve loopback safety. | Keeps `/api/*` loopback-only and marks it deprecated. |

## Related Decisions

- ADR-0001: Brownfield Clean Architecture Migration
- ADR-0007: API Surface and CORS
- ADR-0011: Agent Runtime Levels
- ADR-0021: Bounded Context Consolidation
- ADR-0022: Directory Restructuring
