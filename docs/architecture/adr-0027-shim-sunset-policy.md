# ADR-0027: Shim Sunset Policy

## Status

Accepted

## Date

2026-06-30

## Last Verified

2026-06-30

## Decision Makers

Codex implementation agent; project owner approval via
`C:\Users\WSMAN\.claude\plans\my-doge-micro-fancy-ullman.md`.

## Summary

Compatibility shims remain part of the MY-DOGE-MICRO brownfield migration, but
they are not second implementation homes. This ADR defines the sunset policy for
legacy `/api/*`, `doge.interfaces.api.routers.v1`,
`doge.application.agent.tools`, `doge.application.composition`, and the
demo/test-only in-memory runtime. New behavior belongs in canonical gateway,
tool, bootstrap, and persisted-runtime paths. Shim files may re-export,
delegate, warn, and preserve compatibility contracts only.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python >=3.10, FastAPI 0.123.8, SQLite local persistence, Python/TypeScript SDK clients |
| **Domain** | Runtime, API, compatibility migration |
| **Knowledge Risk** | LOW; the decision records local source-layout and migration policy |
| **References Consulted** | `docs/reference/python/VERSION.md`, ADR-0021, ADR-0022, ADR-0024, ADR-0025, ADR-0026, `docs/progress/runtime-maturity.yaml`, `docs/architecture/file-structure-policy.md`, `docs/architecture/module-boundaries.md`, `src/doge/interfaces/api/routers/v1/`, `src/doge/interfaces/gateway/routers/`, `src/doge/application/composition.py`, `src/doge/application/agent/tools.py`, `src/doge/application/tools/` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | Architecture shim parity tests, import-gate tests, docs validators, maturity honesty validator |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0021, ADR-0022, ADR-0024 |
| **Enables** | Compatibility-surface removal stories, process-root import migration, route/tool shim hardening |
| **Blocks** | Removing a compatibility surface before its parity, migration, and documentation gates are complete |
| **Ordering Note** | This policy tightens ADR-0024 without changing runtime maturity labels or external gate status. |

## Context

### Problem Statement

Sprint G moved the preferred platform path to process roots, persisted runtime,
gateway `/v1` routers, SDK clients, and the canonical tool registry. Several
legacy or compatibility import paths still exist so old callers, demos, and
tests keep working. Without an explicit sunset policy, those compatibility
paths can silently regain behavior and become parallel stacks again.

### Current State

- `/v1` implementation modules live under `doge.interfaces.gateway.routers`.
- `doge.interfaces.api.routers.v1` mirrors the gateway router file set and
  re-exports gateway modules for compatibility.
- `run_stream.py` in the v1 shim package also re-exports `RunStreamHandler` for
  historical static checks; the canonical implementation still lives in the
  gateway route plus handler layer.
- `doge.application.tools` is the canonical tool registry package.
- `doge.application.agent.tools` remains a compatibility import path.
- `doge.application.composition` delegates to bootstrap containers.
- `InMemoryResearchAgentRuntime` remains useful for demos and tests, but the
  persisted runtime is the preferred platform path.
- Legacy `/api/*` remains local loopback compatibility and must not receive new
  platform-only features.

### Constraints

- Brownfield compatibility must remain test-backed until replacement consumers
  and migration notes are complete.
- Public import and HTTP contracts cannot be removed silently.
- Runtime posture remains non-production:
  `production_ready: false`, `stable_declaration: forbidden`, and Level 3
  `experimental`.
- External gates remain operator-controlled.

### Requirements

- Every shim has a canonical replacement path.
- Shim files must not own new behavior.
- Compatibility exceptions must be named and tested.
- Removal requires parity evidence, migration notes, and a rollback plan.
- Maturity documentation must keep demo/test-only paths distinct from
  production-facing paths.

## Decision

### 1. Shim Rule

Shim files may do only these things:

1. Re-export public symbols from the canonical path.
2. Delegate calls to the canonical process root or container.
3. Emit deprecation metadata or warnings when explicitly covered by tests.
4. Preserve historical docstrings required by compatibility/static checks.

Shim files must not introduce new routing logic, persistence access, business
logic, tool implementations, model selection, approval policy, worker behavior,
or feature defaults.

### 2. Compatibility Surface Table

| Surface | Current Status | Canonical Replacement | Removal Preconditions | Earliest Removal |
|---------|----------------|-----------------------|-----------------------|------------------|
| Legacy `/api/*` | Loopback compatibility route family | `/v1/*`, SDKs, and gateway routers | Deprecation headers remain green; route parity and migration notes exist; downstream callers migrate; rollback story approved | Not before 2026-09-30 |
| `doge.interfaces.api.routers` | Legacy local API compatibility package | `doge.interfaces.api_legacy.routers` for legacy local routes and `doge.interfaces.gateway.routers` for gateway routes | All internal and third-party imports migrate; route contract tests prove parity | After import and route migration |
| `doge.interfaces.api.routers.v1` | `/v1` compatibility shim package | `doge.interfaces.gateway.routers` | `test_gateway_router_shim_parity.py` proves no behavior logic; SDK/Web/tests no longer import the old path; `run_stream.py` exception retired or documented | After gateway import migration |
| `doge.application.agent.tools` | Tool registry compatibility shim | `doge.application.tools` | Runtime factories, MCP, tests, and docs use canonical path or named compatibility tests; tool registry parity tests pass | After import parity evidence |
| `doge.application.composition` | Bootstrap compatibility facade | `doge.bootstrap.runtime`, `doge.bootstrap.gateway`, `doge.bootstrap.workspace`, `doge.bootstrap.processes` | Non-allowlisted production imports are gone; tests using it are shim/parity tests only; migration notes name replacements | After process-root migration |
| In-memory runtime | Demo/test-only runtime adapter | Persisted runtime repositories, durable queue, and gateway worker | Deterministic tests have non-in-memory alternatives or explicitly name demo mode; no platform path depends on in-memory state | Separate removal/support story |

### 3. Named Exception: v1 `run_stream.py`

`src/doge/interfaces/api/routers/v1/run_stream.py` may re-export
`RunStreamHandler` from `doge.interfaces.api.handlers` while legacy static tests
depend on that symbol. It may not implement stream behavior. The canonical live
SSE behavior remains `doge.interfaces.gateway.routers.run_stream` plus
`RunStreamHandler`.

### 4. Import Gate Policy

Import checks must distinguish normal production code from intentional
compatibility tests. A repository-wide grep count of zero is not a valid
acceptance criterion while shims remain public. Instead:

- production code under `src/doge` must have no non-allowlisted imports of
  `doge.application.composition`;
- tests that import old paths must be named as shim parity, legacy public
  contract, or migration guard coverage;
- compatibility allowlists must fail when a listed legacy user disappears but
  the allowlist is not updated.

### Architecture Diagram

```text
Legacy caller / old import path
        |
        v
Compatibility shim  -- re-export/delegate/warn only
        |
        v
Canonical path
  - doge.bootstrap.*
  - doge.interfaces.gateway.routers
  - doge.application.tools
  - persisted runtime repositories
```

### Key Interfaces

```python
# Allowed v1 shim shape
from doge.interfaces.gateway.routers.sessions import *  # noqa: F401,F403

# Allowed composition shim shape
def build_research_agent_runtime(...):
    return build_runtime_container(...).build_research_agent_runtime(...)
```

## Alternatives Considered

### Alternative 1: Delete all shims immediately

- **Description**: Remove compatibility imports and legacy routes as soon as the
  canonical paths exist.
- **Pros**: Smallest source tree and simplest conceptual model.
- **Cons**: Breaks brownfield callers, local demos, and migration tests.
- **Rejection Reason**: The project requires staged compatibility with evidence.

### Alternative 2: Keep shims indefinitely with no constraints

- **Description**: Leave legacy paths in place and allow fixes to land wherever
  convenient.
- **Pros**: Lowest short-term friction.
- **Cons**: Recreates parallel stacks and hides ownership boundaries.
- **Rejection Reason**: Conflicts with ADR-0024 single-stack direction.

### Alternative 3: Keep shims with explicit sunset gates

- **Description**: Keep compatibility paths, prohibit behavior growth, and
  remove them only after migration evidence exists.
- **Pros**: Preserves compatibility while keeping canonical ownership clear.
- **Cons**: Requires ongoing architecture and import-gate maintenance.
- **Rejection Reason**: Chosen.

## Consequences

### Positive

- Compatibility paths remain safe for brownfield callers.
- New work has clear canonical targets.
- Architecture tests can distinguish shim parity from accidental new coupling.
- Removal stories have concrete preconditions.

### Negative

- Some duplicate public import paths remain until migration evidence is complete.
- Tests must maintain allowlists and exception explanations.
- Developers must resist small convenience edits inside shim files.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Shim accumulates behavior again | MEDIUM | HIGH | Parity tests and file-structure policy prohibit non-re-export logic. |
| Import gates reject intentional compatibility tests | MEDIUM | MEDIUM | Tests classify shim/parity imports separately from production imports. |
| External consumers keep old paths indefinitely | MEDIUM | MEDIUM | Removal requires migration notes and follow-up removal stories. |
| Maturity posture is overstated because a demo path works | LOW | HIGH | Runtime maturity validator preserves non-production labels and external-gate status. |

## CDD Requirements Addressed

| CDD System | Requirement | How This ADR Addresses It |
|------------|-------------|--------------------------|
| `bc-06-agent-runtime.md` | Runtime owns sessions, runs, events, workers, approvals, artifacts, and state transitions without absorbing interface or adapter responsibilities. | Keeps runtime compatibility imports from becoming alternate implementation owners and points production-facing work to persisted runtime paths. |
| `sdk-daemon-client-interfaces.md` | SDKs must use `/v1/*` for daemon runtime workflows, and legacy `/api/*` routes remain product compatibility routes. | Defines `/v1` gateway routers as canonical and legacy `/api/*` as compatibility only. |
| `clean-architecture-migration.md` | Brownfield compatibility must be staged and test-backed. | Requires parity tests, migration notes, and removal gates before compatibility paths are deleted. |
| `fastapi-service.md` | Local API compatibility must preserve loopback-safe behavior while platform routes converge. | Allows legacy local routes to remain but blocks new platform-only features there. |

## Performance Implications

- **CPU**: No runtime impact; this is a source-layout and migration policy.
- **Memory**: No runtime impact.
- **Load Time**: Compatibility imports remain lightweight delegates/re-exports.
- **Network**: No network behavior changes.

## Migration Plan

1. Keep `doge.interfaces.api.routers.v1` as re-export shims and document the
   `run_stream.py` exception.
2. Keep `doge.application.composition` as a bootstrap delegate while normal
   callers migrate to process roots.
3. Keep `doge.application.agent.tools` as a re-export shim while callers migrate
   to `doge.application.tools`.
4. Preserve legacy `/api/*` deprecation metadata and route tests until the
   documented sunset window and migration stories close.
5. Track in-memory runtime as demo/test-only until deterministic tests no longer
   need it or a separate support story keeps it intentionally.

## Validation Criteria

- `tests/unit/architecture/test_gateway_router_shim_parity.py` passes.
- `tests/unit/architecture/test_bootstrap_owns_factories.py` passes.
- `tests/unit/layer_gates/test_new_code_imports.py` passes.
- `tests/unit/layer_gates/test_composition_root_location.py` passes.
- `scripts/validate_docs_links.py` passes.
- `scripts/validate_alpha_maturity_honesty.py` continues to preserve
  non-production posture.

## Related Decisions

- ADR-0021: Bounded Context Consolidation
- ADR-0022: Directory Restructuring
- ADR-0024: Single-Stack Runtime Direction
- ADR-0025: Runtime Streaming Semantics
- ADR-0026: Artifact Citation Assembly
