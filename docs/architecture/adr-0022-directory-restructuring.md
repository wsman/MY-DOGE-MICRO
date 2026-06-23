# ADR-0022: Directory Restructuring

## Status
Proposed

## Date
2026-06-23

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python >=3.10, FastAPI 0.123.8, Pydantic 2.12.4, SQLite, DuckDB |
| **Domain** | Source Layout / Compatibility Migration |
| **Knowledge Risk** | LOW for Python package layout; MEDIUM for package move blast radius |
| **References Consulted** | `docs/reference/python/VERSION.md`, `docs/architecture/adr-0001-brownfield-clean-architecture.md`, `docs/architecture/adr-0021-bounded-context-consolidation.md`, `docs/progress/platformization-consolidation-baseline.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | Import compatibility tests, layer gates, contract tests, package build checks |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0001, ADR-0021 |
| **Enables** | Facade package creation, staged provider migration, router service extraction |
| **Blocks** | Big-bang physical moves before compatibility exports and boundary tests exist |
| **Ordering Note** | This ADR proposes the target structure only; physical moves require follow-up stories and green compatibility gates. |

## Context

### Problem Statement

The proposed bounded contexts need a source layout that communicates ownership,
but the current implementation still relies on established `core`,
`application`, `infrastructure`, and `interfaces` paths. A big-bang directory
move would risk breaking API, Web, SDK, CLI, MCP, and tests at the same time.

### Current State

The repo uses a Clean Architecture tree under `src/doge/` with domain,
application, infrastructure, and interface packages. Recent platformization
slices added platform routers, runtime, capability registry, SDKs, and Web
shell behavior behind feature flags. Several public imports and tests already
depend on the current package paths.

### Constraints

- Existing import paths must continue to work during migration.
- Manual code moves must be small, testable, and reversible.
- Public SDK/API contracts are more important than internal naming.
- Only the composition/bootstrap layer may wire products, platform services,
  and concrete adapters together.
- This decision must not imply production readiness.

### Requirements

- Define a target package layout aligned with ADR-0021.
- Prefer facade packages and compatibility exports before physical moves.
- Preserve old imports with deprecation markers and removal criteria.
- Add tests that prove old and new imports resolve to the same behavior.
- Keep physical relocation behind explicit stories and validation gates.

## Decision

Adopt the following target layout as the destination for staged migration:

```text
src/doge/
+-- shared/
+-- platform/
|   +-- workspace/
|   +-- runtime/
|   +-- evidence/
|   +-- governance/
+-- products/
|   +-- market/
|   +-- research/
|   +-- portfolio/
|   +-- quant/
+-- adapters/
|   +-- models/
|   +-- market_data/
|   +-- financial_data/
|   +-- persistence/
|   +-- vector/
|   +-- eventing/
|   +-- secrets/
+-- entrypoints/
|   +-- api/
|   +-- daemon/
|   +-- cli/
|   +-- mcp/
+-- bootstrap/
```

The migration starts with shallow facade packages and compatibility exports.
For example, a future `doge.platform.runtime` package may re-export an existing
runtime type while the old import remains available:

```python
# old path remains valid during the compatibility window
from doge.application.agent.tools import ToolRegistry

# new path becomes the preferred import once the facade exists
from doge.platform.runtime import ToolRegistry
```

Physical movement of implementation files is deferred until:

- ADR-0021 and ADR-0022 are accepted or the specific story explicitly declares
  it is working under Proposed ADR gates.
- Compatibility import tests exist for each moved public symbol.
- Layer gates and relevant API/SDK/runtime contract tests are green.
- Deprecation notes identify old path, new path, and removal version or phase.

### Target Package Responsibilities

| Package | Responsibility |
|---------|----------------|
| `shared` | Cross-context primitives such as config, errors, ids, clock, and contracts. |
| `platform/workspace` | Workspace, Project, Research Case, Workflow Template, and capability catalog relationships. |
| `platform/runtime` | Session, Run, Event, Worker, model execution, tool execution, artifacts, cancellation. |
| `platform/evidence` | Document, chunk, retrieval, claim, citation, provenance, summary, eval read models. |
| `platform/governance` | Identity, tenant, ACL, entitlement, audit, secrets, budget, eval, maturity gates. |
| `products/market` | Market scans, RSRS, breadth, anomalies, watchlists, market reports. |
| `products/research` | Macro, company, industry, earnings review, memos, research versions. |
| `products/portfolio` | Holdings, exposure, concentration, risk, scenarios, rebalance drafts. |
| `products/quant` | SQL, Python, factors, backtests, data jobs, code tasks. |
| `adapters` | Concrete provider, persistence, model, vector, eventing, and secret implementations. |
| `entrypoints` | FastAPI, CLI, daemon, MCP, and other delivery protocols. |
| `bootstrap` | Composition roots that connect bounded contexts to adapters and entrypoints. |

## Alternatives Considered

### Alternative 1: Big-Bang Physical Move

- **Description**: Move all files into the target tree immediately.
- **Pros**: Directory layout becomes clean quickly.
- **Cons**: High breakage risk across tests, API routes, SDK clients, and
  legacy imports.
- **Rejection Reason**: The project is brownfield and compatibility is a
  control-manifest requirement.

### Alternative 2: Documentation-Only Layout

- **Description**: Document the target tree but never add packages or facades.
- **Pros**: No implementation risk.
- **Cons**: Does not guide imports, story work, or provider migration.
- **Rejection Reason**: The plan requires staged migration toward real package
  boundaries.

### Alternative 3: Facade-First Migration

- **Description**: Add target packages as facades, migrate callers gradually,
  then move implementations after compatibility and boundary tests pass.
- **Pros**: Preserves behavior, allows small PRs, and gives tests a stable
  migration target.
- **Cons**: Creates temporary duplicate import paths.
- **Rejection Reason**: Chosen.

## Consequences

### Positive

- Source layout can align with bounded contexts without breaking current users.
- Old imports remain testable while new imports are introduced.
- Boundary tests can be added before risky moves.
- Entry points and adapters can be clearly separated from product logic.

### Negative

- Facade packages add temporary indirection.
- Deprecation tracking is required to prevent permanent dual paths.
- Developers must learn both old and new paths during the migration window.

### Risks

- **Risk**: Compatibility exports hide stale implementation ownership.
  **Mitigation**: Every compatibility export must name its target path and
  removal gate.
- **Risk**: Facades become new business-logic homes.
  **Mitigation**: Control Manifest forbids business decisions in adapters and
  requires shallow module internals until scale justifies deeper packages.
- **Risk**: Tests validate imports but not behavior.
  **Mitigation**: Import tests must be paired with existing API, SDK, runtime,
  and provider parity tests.

## CDD Requirements Addressed

| CDD System | Requirement | How This ADR Addresses It |
|------------|-------------|--------------------------|
| `bc-01-market-intelligence.md` through `bc-08-governance-evaluation.md` | Provide package destinations for bounded contexts. | Defines the target package tree. |
| `clean-architecture-migration.md` | Preserve incremental migration and compatibility. | Requires facade-first migration and old import compatibility. |
| `sdk-daemon-client-interfaces.md` | Preserve public client contracts while internals change. | Blocks physical moves until SDK/API contract tests pass. |
| `control-manifest.md` | Enforce layer and dependency rules. | Adds boundary and deprecation rules for staged migration. |

## Performance Implications

- **CPU**: Import facades have negligible runtime cost.
- **Memory**: Minimal module-object overhead during compatibility windows.
- **Load Time**: Slight import indirection until implementation moves finish.
- **Network**: No impact.
- **Operational Cost**: Short-term documentation and test overhead prevents
  larger migration regressions.

## Migration Plan

1. Record the target layout in this ADR and the Control Manifest.
2. Add facade packages only when a story migrates a specific public symbol.
3. Keep old imports as re-exports with deprecation metadata.
4. Add compatibility import tests and boundary tests for each migrated symbol.
5. Migrate internal callers from old imports to new imports in small batches.
6. Remove old paths only after the stated removal version or phase and green
   contract tests.

## Validation Criteria

- New target packages are shallow and do not duplicate full four-layer trees.
- Old imports and new facade imports resolve during the compatibility window.
- Layer gates remain green after each package addition.
- API, runtime, SDK, and provider parity tests pass after each physical move.
- Deprecated paths identify replacement path and removal gate.
- No physical move happens solely because this ADR exists.

## Related Decisions

- ADR-0001: Brownfield Clean Architecture Migration
- ADR-0011: Agent Runtime Levels
- ADR-0019: Capability Registry
- ADR-0021: Bounded Context Consolidation
