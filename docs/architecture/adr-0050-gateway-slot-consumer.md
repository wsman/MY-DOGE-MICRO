# ADR-0050: Gateway Slot Consumer

## Status

Accepted

## Date

2026-07-07

## Decision Makers

wsman (product owner) / implementation agent

## Summary

Sprint 041 consumes the `gateway` slot facet at the `/v1` route registration
seam. The sprint adds one built-in gateway route slot, `gateway.slots`, that
contributes the existing read-only slot discovery router.

When `DOGE_FEATURE_SLOT_PLATFORM` is off, `_register_v1_routes()` still mounts
the slots router directly, preserving the current route set and the endpoint's
own 404 feature gate. When the flag is on, `_register_v1_routes()` mounts
`gateway.slots` through `GatewayRouteContribution` and skips the direct
hardcoded slots-router include. The resulting route set is equivalent.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python 3.10+; FastAPI; existing gateway routers; existing slot facet dataclasses |
| **Domain** | API Gateway, v1 route registration, slot discovery |
| **Knowledge Risk** | LOW - local route wiring over an existing router |
| **References Consulted** | `docs/architecture/adr-0042-slot-platform.md`, `docs/architecture/adr-0043-slot-contribution-facets.md`, `docs/architecture/adr-0045-slot-discovery-surfaces.md`, `docs/architecture/adr-0049-data-slot-consumer.md`, `src/doge/interfaces/api/routes.py`, `src/doge/interfaces/gateway/routers/slots.py`, `src/doge/platform/slots/facets.py`, `C:\Users\WSMAN\.claude\plans\openclaw-like-magical-barto.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | gateway slot unit tests, gateway slot parity tests, CLI/API/doged slot status tests, route coverage regressions, import boundaries, docs validators, maturity honesty, plan closure, whitespace checks |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0007 (API Surface and CORS), ADR-0042 (Slot Platform Foundation), ADR-0043 (Slot Contribution Facets), ADR-0045 (Slot Discovery Surfaces), ADR-0049 (Data Slot Consumer) |
| **Extends** | ADR-0043 by adding a runtime consumer for the `routes` facet |
| **Supersedes** | None |
| **Enables** | Later migration of additional `/v1` routers, SlotKernel route assembly, and route/bundle policy |
| **Blocks** | None |

## Context

`GatewayRouteContribution` already existed as a typed slot facet, but no runtime
factory consumed it. `/v1` route registration was still fully hardcoded in
`src/doge/interfaces/api/routes.py`.

The lowest-risk first gateway consumer is the slots discovery router itself. It
already exists, is read-only, and is feature-gated. Moving this one router
through a gateway slot proves the contribution path without changing the rest
of the API surface.

## Constraints

- Keep `DOGE_FEATURE_SLOT_PLATFORM` default `false`.
- Preserve the `/v1` route set and endpoint behavior.
- Keep legacy `/api/*` route mounting unchanged.
- Keep `doge.platform.slots` pure and framework-free.
- Put the concrete gateway slot beside gateway interface code, not in
  `platform.slots`.
- Defer migration of sessions, runs, documents, portfolios, platform, tools,
  audit, enterprise, and health routers.
- Do not add `/v1/slot-bundles`, bundle activation, route policy enforcement,
  active route health, Web Slot Center, SDK slot client, third-party install,
  signing, or SlotKernel lifecycle orchestration.
- Do not close external/operator gates or change production maturity posture.

## Decision

Add `doge.interfaces.gateway.slot.SlotDiscoveryGatewaySlot`. It declares
`gateway.slots`, type `gateway`, owner `api-gateway`, capabilities
`gateway.routes` and `slot.discovery`, and one route contribution:

```python
GatewayRouteContribution(
    router_id="gateway.slots",
    router_factory=lambda context: slots_router.router,
    prefix="/v1",
    tags=("v1-slots",),
    requires_auth=True,
)
```

Add `build_slot_aware_gateway_routes(target_app, settings=...)` to
`src/doge/bootstrap/runtime_factories/slots.py`. It resolves gateway slots whose
feature flags are satisfied, rejects duplicate router IDs, rejects route
factories that return no router, mounts routers via `target_app.include_router`,
and returns mounted router IDs.

Update `_register_v1_routes(target_app, settings=None)` so it mounts
`gateway.slots` through slot contributions when slot platform is enabled. If
`gateway.slots` is not mounted, it falls back to the existing hardcoded
`v1_slots.router` include. `register_routes()` passes settings through to this
function.

## Alternatives Considered

### Alternative 1: Convert every `/v1` router in one sprint

- **Description**: Move sessions, runs, documents, portfolios, platform, slots,
  tools, audit, enterprise, and health routers to gateway slots at once.
- **Pros**: More complete gateway slot story immediately.
- **Cons**: Larger route-order, dependency, OpenAPI, and auth blast radius.
- **Rejection Reason**: Sprint 041 is a consumer proof. One read-only router is
  enough to validate the facet before broad migration.

### Alternative 2: Put gateway slot providers in `doge.platform.slots`

- **Description**: Keep all built-in providers close to the slot contract.
- **Pros**: Easy to discover from the slot package.
- **Cons**: Would make `platform.slots` import FastAPI/interface modules,
  violating ADR-0042 purity.
- **Rejection Reason**: Concrete route providers belong beside gateway
  interface code; bootstrap owns consumption.

### Alternative 3: Remove the hardcoded slots-router fallback

- **Description**: Mount `/v1/slots` only through gateway slots.
- **Pros**: Cleaner route registration when slot platform exists.
- **Cons**: Changes flag-off route availability from "mounted but endpoint
  gated with 404" to "not mounted", breaking current parity.
- **Rejection Reason**: Flag-off behavior must remain unchanged.

## Consequences

### Positive

- The `gateway` facet now has a real runtime consumer.
- Route slot contributions can mount FastAPI routers through bootstrap wiring.
- `/v1/slots` route behavior remains equivalent.
- Duplicate router IDs fail fast.
- Discovery surfaces list `gateway.slots`.

### Negative

- Only the slots discovery router is slot-backed; most `/v1` routers remain
  hardcoded.
- Route permissions and health remain declarative only.
- The consumer is assembled through current runtime factories rather than a
  first-class `SlotKernel`.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Route set changes under slot platform | LOW | HIGH | Parity test compares flag-on and flag-off `/v1` route rows. |
| Duplicate router IDs mount conflicting routers | LOW | MEDIUM | Consumer rejects duplicate `router_id`. |
| Gateway slot import triggers API container side effects | LOW | MEDIUM | Router import is delayed until `router_factory` execution. |
| Operators mistake gateway slot proof for full route modularization | LOW | MEDIUM | ADR/CDD/evidence keep remaining routers, bundles, policy, and production gates out of scope. |

## CDD Requirements Addressed

| CDD System | Requirement | How This ADR Addresses It |
|------------|-------------|--------------------------|
| `design/cdd/sprint-041-gateway-slot-consumer.md` | Gateway route slots can contribute routers consumed by API route registration. | Adds `gateway.slots` and `build_slot_aware_gateway_routes()`. |
| `design/cdd/fastapi-service.md` | `/v1` gateway routes remain the primary API surface. | Keeps the route set equivalent and preserves `/v1/slots` behavior. |
| `docs/architecture/adr-0045-slot-discovery-surfaces.md` | Slot discovery remains read-only and feature-gated. | Routes are contributed by slot only when `slot_platform` is enabled; endpoint gating remains. |

## Performance Implications

- **CPU**: one small route-contribution loop during app route registration when
  slot platform is enabled.
- **Memory**: no new runtime state after router registration.
- **Load Time**: imports the gateway slot provider when the built-in slot
  registry is built; actual router import is lazy.
- **Network**: none.

## Migration Plan

1. Add `SlotDiscoveryGatewaySlot`.
2. Register the gateway slot in the built-in slot registry.
3. Add `build_slot_aware_gateway_routes()`.
4. Update `_register_v1_routes()` to use gateway slots when enabled and direct
   fallback otherwise.
5. Extend CLI/API/doged slot discovery expectations for `gateway.slots`.
6. Keep full router migration, bundles, route policy, active route health,
   SlotKernel, loaders, signing, and third-party install deferred.

## Validation Criteria

- `gateway.slots` manifest is typed as `gateway`, declares `slot_platform`, and
  provides gateway route capabilities.
- With slot platform off, `/v1/slots` remains mounted directly and endpoint
  gating behavior is unchanged.
- With slot platform on, `/v1/slots` is mounted through `gateway.slots` and the
  `/v1` route set is equivalent.
- Duplicate router IDs fail fast.
- Route factories returning no router fail fast.
- CLI/API/doged slot discovery lists `gateway.slots`.
- Maturity posture remains `production_ready: false`,
  `stable_declaration: forbidden`, and `level_3_sdk_platform: experimental`.

## Related Decisions

- ADR-0007: API Surface and CORS
- ADR-0042: Slot Platform Foundation
- ADR-0043: Slot Contribution Facets
- ADR-0045: Slot Discovery Surfaces
- ADR-0049: Data Slot Consumer
