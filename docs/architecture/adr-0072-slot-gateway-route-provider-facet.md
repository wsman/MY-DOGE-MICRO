# ADR-0072: Slot Gateway Route Provider Facet

## Status

Accepted

## Date

2026-07-09

## Decision Makers

wsman (product owner) / implementation agent

## Summary

P10 opens the final previously restricted installed-provider facet: `routes`.
Installed third-party providers may now contribute gateway route routers when
they pass the existing ADR-0064/0065 provider execution chain.

Provider routes are not arbitrary top-level mounts. Non-built-in route
providers must mount under `/v1/slot-providers/<slot_id>`, must declare
`requires_auth=True`, and are included with the existing
`deps.require_api_token` dependency. Route factories and request handlers run
with slot permission context when runtime interception is enabled.

This completes P10 restricted facet expansion, but it does not change the
default-off provider execution chain. It does not add marketplace behavior,
YAML manifests, URL/upload install, OS/container/WASM sandboxing, transitive
dependency signing, provider malicious-code containment, external gate closure,
or production maturity.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python 3.10+; FastAPI APIRouter; existing Slot Platform gateway route consumer |
| **Domain** | Slot Platform gateway route provider facet |
| **Knowledge Risk** | HIGH - provider routes add in-process HTTP handlers to the daemon surface |
| **References Consulted** | `docs/reference/python/VERSION.md`, `docs/architecture/adr-0050-gateway-slot-consumer.md`, `docs/architecture/adr-0064-slot-provider-execution.md`, `docs/architecture/adr-0065-provider-package-identity.md`, `docs/architecture/adr-0071-slot-governance-policy-provider-facet.md`, `design/cdd/sprint-041-gateway-slot-consumer.md`, `C:\Users\WSMAN\.claude\plans\openclaw-rippling-sparkle.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | provider route tests, gateway route parity tests, route coverage, slot API/CLI regression, governance validators, whitespace checks |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0043 (Slot Contribution Facets), ADR-0050 (Gateway Route Slot Consumer), ADR-0064 (Slot Provider Execution), ADR-0065 (Provider Package Identity), ADR-0066 (Code-String Isolation Prototype), ADR-0067 (Install Surfaces), ADR-0068 (Eval Suite Provider Facet), ADR-0069 (UI Panel Provider Facet), ADR-0070 (Watcher Provider Facet), ADR-0071 (Governance Policy Provider Facet) |
| **Extends** | ADR-0064 by moving `routes` from restricted provider facets into the installed-provider allowlist with namespace/auth constraints |
| **Supersedes** | ADR-0064's "gateway routes are not executable from installed third-party providers" statement, only for the default-off local provider path |
| **Enables** | Completion of P10 restricted facet expansion |
| **Blocks** | Any claim that P10 enables marketplace install, arbitrary route mounts, provider sandboxing, external gate closure, or production maturity |

## Context

ADR-0050 already introduced the built-in gateway route consumer for
`gateway.slots`, allowing Slot Platform-owned routers to mount into the
canonical `/v1` app path. P10 routes are the highest-risk restricted facet
because provider route handlers become HTTP entrypoints.

Opening route providers therefore keeps all provider execution gates and adds
provider-specific route constraints:

- route providers use a namespace below `/v1/slot-providers/<slot_id>`;
- route providers must require auth;
- route providers receive the existing API token dependency;
- route factories and request handlers receive slot permission context when
  runtime interception is enabled.

The default app route table remains the canonical documented 98 HTTP routes
unless an operator installs and enables additional provider routes.

## Constraints

- Keep all provider execution gates from ADR-0064/0065.
- Allow only `SlotType.GATEWAY` providers to contribute `routes`.
- Keep provider routes under `/v1/slot-providers/<slot_id>`.
- Reject provider routes that set `requires_auth=False`.
- Include provider routes with `deps.require_api_token`.
- Execute route factories and request handlers with active slot permission
  context when runtime interception is enabled.
- Keep dynamic provider routes outside the default 98-route static documentation
  count unless a concrete installed provider is documented separately.
- Keep `production_ready: false`, `stable_declaration: forbidden`, and
  `level_3_sdk_platform: experimental`.

## Decision

`InstalledProviderSlot` now treats `SlotType.GATEWAY` as provider-executable
and maps it to the single allowed contribution field `routes`.

`build_slot_aware_gateway_routes()` now validates provider routes before
including them:

```text
InstalledProviderSlot
  -> SlotKernel.resolve_contributions(slot_type=SlotType.GATEWAY)
  -> build_slot_aware_gateway_routes()
  -> FastAPI.include_router(prefix=/v1/slot-providers/<slot_id>)
```

Route providers must declare `requires_auth=True`. The mounted router receives
both the API token dependency and, when runtime interception is enabled, a
yield dependency that keeps `slot_permission_context(...)` active during
request handling.

Contribution validation still rejects any contribution field that belongs to a
different slot type.

## Alternatives Considered

### Alternative 1: Keep routes restricted

- **Pros**: Avoids the broadest in-process attack surface.
- **Cons**: Leaves the Slot Platform unable to expose installed provider HTTP
  affordances even for trusted local operators.
- **Rejection Reason**: P10 ordered routes last and adds namespace/auth/scope
  constraints while keeping provider execution default off.

### Alternative 2: Allow arbitrary provider prefixes

- **Pros**: More flexible routing.
- **Cons**: Providers could shadow or confuse canonical `/v1` routes.
- **Rejection Reason**: Provider routes must stay under the explicit provider
  namespace.

### Alternative 3: Rely only on provider-declared `requires_auth`

- **Pros**: Simpler mount logic.
- **Cons**: Metadata alone does not enforce request authentication.
- **Rejection Reason**: The mount path now injects the existing API token
  dependency for provider routes.

## Consequences

### Positive

- Signed local providers can expose bounded HTTP affordances through the
  governed provider path.
- Provider route handlers can observe slot permission context during requests.
- Provider routes cannot mount over arbitrary canonical `/v1` paths.

### Negative

- Provider route code still runs in-process when default-off gates are enabled.
- Provider route handlers add operator-installed HTTP surface area outside the
  default static route table.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Provider route shadows canonical API routes | LOW | HIGH | Non-built-in provider prefixes must be `/v1/slot-providers/<slot_id>`. |
| Provider route omits auth | LOW | HIGH | `requires_auth=False` is rejected and provider routers receive `deps.require_api_token`. |
| Provider route handler bypasses in-process guards | MEDIUM | HIGH | Slot scope wraps request handling for guarded ports, but ADR states this is not malicious-code containment. |

## CDD Requirements Addressed

| CDD System | Requirement | How This ADR Addresses It |
|------------|-------------|--------------------------|
| `design/cdd/p10-gateway-route-provider-facet.md` | Allow gateway route provider facets only after namespace, auth, and slot-scope constraints are explicit. | Opens only `routes`, enforces provider namespace/auth, and wraps request handling in slot permission context. |
| `design/cdd/sprint-041-gateway-slot-consumer.md` | Gateway route slots can mount FastAPI routers through the route consumer. | Reuses `build_slot_aware_gateway_routes()` and `GatewayRouteContribution`. |
| `design/cdd/p5-slot-provider-execution.md` | Restricted facets must fail closed unless a later ADR accepts one. | Supersedes the final route restriction under default-off provider execution gates. |

## Validation Criteria

- Installed signed gateway provider resolves through
  `build_slot_aware_gateway_routes()`.
- Provider routes require the existing API token dependency.
- Provider route handlers run with active slot permission context.
- Provider routes must mount below `/v1/slot-providers/<slot_id>`.
- Route facets are rejected when contributed by non-gateway slot types.
- Built-in gateway route parity tests still pass.
- Default route coverage remains at 98 documented routes.
- Slot API/CLI regression passes.
- Governance validators pass and maturity posture remains unchanged.

## Related Decisions

- [ADR-0050: Gateway Slot Consumer](adr-0050-gateway-slot-consumer.md)
- [ADR-0064: Slot Provider Execution](adr-0064-slot-provider-execution.md)
- [ADR-0065: Provider Package Identity](adr-0065-provider-package-identity.md)
- [ADR-0071: Slot Governance Policy Provider Facet](adr-0071-slot-governance-policy-provider-facet.md)
