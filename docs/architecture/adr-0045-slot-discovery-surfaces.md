# ADR-0045: Slot Discovery Surfaces

## Status

Accepted

## Date

2026-07-07

## Decision Makers

wsman (product owner) / implementation agent

## Summary

Sprint 036 exposes the built-in Slot Platform status through read-only operator
surfaces: `/v1/slots`, `/v1/slots/{slot_id}`,
`/v1/slots/{slot_id}/health`, and `doged slots`.

The surfaces read manifests, static health, feature flags, and derived
`resolved` / `disabled` status only. They do not resolve slot contributions,
invoke lifecycle hooks, enable or disable slots, activate bundles, install
third-party slots, or enforce runtime permissions.

## Status Update - 2026-07-08

ADR-0058 makes read-only built-in slot discovery available by default through the
controlled local Slot Platform path. Discovery remains read-only; activation,
install, provider execution, signing, sandboxing, and marketplace behavior are
still gated or absent.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python 3.10+; FastAPI; argparse daemon CLI; existing slot dataclasses |
| **Domain** | Gateway/API discovery and local daemon operator diagnostics |
| **Knowledge Risk** | LOW - additive FastAPI routes and CLI rows over existing manifests |
| **References Consulted** | `docs/architecture/adr-0042-slot-platform.md`, `docs/architecture/adr-0043-slot-contribution-facets.md`, `docs/architecture/adr-0044-workflow-slot-consumer.md`, `src/doge/bootstrap/runtime_factories/slots.py`, `src/doge/interfaces/api/routes.py`, `src/doge/interfaces/daemon/main.py`, `C:\Users\WSMAN\.claude\plans\openclaw-like-magical-barto.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | slot API contract tests, doged CLI tests, CLI slots tests, route coverage, governance route sync, SDK contract, import boundaries, docs validators, maturity honesty, plan closure, whitespace checks |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0042 (Slot Platform Foundation), ADR-0043 (Slot Contribution Facets), ADR-0044 (Workflow Slot Consumer), ADR-0007 (API Surface and CORS), ADR-0033 (Local Daemon Operator CLI) |
| **Extends** | ADR-0042 by adding read-only discovery surfaces for the built-in registry |
| **Supersedes** | None |
| **Enables** | Future Web Slot Center, bundle graph exposure, and operator slot doctor commands |
| **Blocks** | None |

## Context

The Slot Platform roadmap requires users and operators to inspect what slots are
installed, whether their feature flags are satisfied, what they provide, and how
their static health is declared. Before this sprint, `doge slots list/show`
existed, but daemon operators and API consumers had no `/v1` discovery surface
and no `doged` command.

The project is still experimental. Exposing slot discovery must therefore be
more conservative than exposing runtime activation. This sprint makes status
visible without adding mutation or third-party installation.

## Constraints

- Keep `DOGE_FEATURE_SLOT_PLATFORM` default `false`.
- Gate `/v1/slots` routes behind `DOGE_FEATURE_SLOT_PLATFORM`.
- Keep `doged slots` useful even when flags are off by showing disabled rows.
- Do not call `slot.resolve()` from discovery surfaces.
- Do not create `/v1/slot-bundles` or bundle activation endpoints.
- Do not add SDK package source, Web Slot Center, persistence schema, runtime
  dispatch, ModelRouter/ProfileRegistry, watcher middleware, or permission
  enforcement changes.
- Do not close external/operator gates or change production maturity posture.

## Decision

Add `build_slot_status_rows(settings=None)` in
`src/doge/bootstrap/runtime_factories/slots.py`. The helper constructs the
built-in registry, derives feature-flag status through `SlotRegistry.status()`,
and serializes each manifest into a JSON-safe row containing:

- id, name, version, type, owner, maturity, description, and entrypoint
- status (`resolved` or `disabled`)
- feature flags
- provides tools/capabilities/metadata
- requirements
- declarative permissions
- static health
- compatibility metadata
- count summaries

The helper intentionally reads manifests and settings only. It does not resolve
contributions and therefore does not construct tool services, model clients,
database adapters, or network clients.

Update `doge slots list` to use the shared row helper for list output while
keeping its existing feature-disabled message and manifest `show` behavior.

Add `src/doge/interfaces/gateway/routers/slots.py` with read-only routes:

- `GET /v1/slots`
- `GET /v1/slots/{slot_id}`
- `GET /v1/slots/{slot_id}/health`

The router uses the same token dependency as other v1 routers and returns 404
with `slot platform API disabled` when `DOGE_FEATURE_SLOT_PLATFORM` is off.
Unknown slot IDs return 404 with `slot not found`.

Update `_register_v1_routes()` to mount the slots router under `/v1`.

Add `doged slots [--json]` to `src/doge/interfaces/daemon/main.py`. The text
output is compact for operator scans; the JSON output returns the same shared
row shape as the API.

Update API route authority from 90 to 93 HTTP routes:

- 34 legacy `/api/*` compatibility routes
- 59 daemon/v1 and health routes

No `/v1/slot-bundles` route is added in this sprint.

## Alternatives Considered

### Alternative 1: Expose only `doge slots`

- **Description**: Keep discovery in the existing CLI command and skip API and
  daemon operator surfaces.
- **Pros**: Smaller surface.
- **Cons**: Does not satisfy daemon/operator discovery and gives Web/SDK
  integrators no future-compatible `/v1` contract to read.
- **Rejection Reason**: Read-only API discovery is a low-risk prerequisite for
  later Slot Center and SDK capability checks.

### Alternative 2: Resolve contributions before reporting status

- **Description**: Call `slot.resolve()` so counts and health could reflect
  live contribution objects.
- **Pros**: Closer to runtime assembly.
- **Cons**: Could construct tool/model/database services from a diagnostic
  endpoint, increasing side effects and failure modes.
- **Rejection Reason**: Discovery must be manifest-only until lifecycle,
  permission, and health semantics are first-class.

### Alternative 3: Add bundle endpoints now

- **Description**: Add `/v1/slot-bundles` beside `/v1/slots`.
- **Pros**: Closer to the final roadmap.
- **Cons**: Bundle activation, mutation authorization, persistence, and
  enterprise policy are not implemented.
- **Rejection Reason**: A read-only slot list is safe now; bundle APIs would
  imply activation semantics that do not exist yet.

## Consequences

### Positive

- API consumers can discover built-in slot status through `/v1/slots`.
- Daemon operators can inspect slot posture with `doged slots`.
- CLI/API/daemon use one serialized row shape.
- Route authority is updated and covered by docs-vs-live tests.

### Negative

- Discovery is limited to built-in slots.
- Health is static manifest health, not active probes.
- There is still no `SlotKernel`, bundle graph, watcher enforcement, or
  third-party installation path.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Discovery endpoint accidentally constructs runtime services | LOW | MEDIUM | Shared helper uses `SlotRegistry.status()` only and never calls `slot.resolve()`. |
| Route table drifts after adding `/v1/slots` | LOW | MEDIUM | Route coverage and S017 governance route tests assert 93 rows and live parity. |
| Operators mistake read-only status for production maturity | LOW | MEDIUM | ADR/CDD/evidence keep maturity experimental and production readiness false. |
| Bundle APIs appear available before implementation | LOW | MEDIUM | Contract test asserts `/v1/slot-bundles` remains unavailable. |

## CDD Requirements Addressed

| CDD System | Requirement | How This ADR Addresses It |
|------------|-------------|--------------------------|
| `design/cdd/sprint-036-slot-discovery-surfaces.md` | Built-in slot status is visible through API and daemon operator surfaces. | Adds `/v1/slots` routes and `doged slots`. |
| `design/cdd/fastapi-service.md` | Every product route must be documented and route-covered. | Updates route authority to 93 and route coverage tests. |
| `design/cdd/bc-06-agent-runtime.md` | Runtime/operator diagnostics remain local, explicit, and maturity-honest. | Adds read-only daemon slot inspection without activation. |

## Performance Implications

- **CPU**: negligible; iterates the small built-in registry.
- **Memory**: small JSON row construction.
- **Load Time**: importing the built-in slot registry mirrors existing CLI slot
  behavior.
- **Network**: none.

## Migration Plan

1. Add shared manifest-only slot status rows in bootstrap.
2. Reuse the rows in `doge slots list`.
3. Add feature-gated `/v1/slots` read routes.
4. Add `doged slots [--json]`.
5. Update route authority from 90 to 93.
6. Keep bundle, install, mutation, Web, SDK, and runtime enforcement work
   deferred.

## Validation Criteria

- `/v1/slots` returns 404 when `DOGE_FEATURE_SLOT_PLATFORM` is off.
- `/v1/slots` lists built-in slots and marks nested workflow slots disabled
  unless their own feature flag is on.
- `/v1/slots/{slot_id}` and `/health` return one slot's manifest/status and
  static health.
- Unknown slot IDs return 404.
- `/v1/slot-bundles` remains unavailable.
- `doged slots` prints text rows and `doged slots --json` returns shared rows.
- Route coverage and governance route sync pass at 93 routes.
- Maturity posture remains `production_ready: false`,
  `stable_declaration: forbidden`, and `level_3_sdk_platform: experimental`.

## Related Decisions

- ADR-0007: API Surface and CORS
- ADR-0033: Local Daemon Operator CLI
- ADR-0042: Slot Platform Foundation
- ADR-0043: Slot Contribution Facets
- ADR-0044: Workflow Slot Consumer
