# ADR-0069: Slot UI Panel Provider Facet

## Status

Accepted

## Date

2026-07-09

## Decision Makers

wsman (product owner) / implementation agent

## Summary

P10 opens the second previously restricted installed-provider facet:
`ui_panels`. Installed third-party providers may now contribute UI panel
metadata when they pass the existing ADR-0064/0065 provider execution chain and
when `DOGE_FEATURE_SLOT_UI` is explicitly enabled.

This is metadata-only. The backend does not import Vue modules, and the current
frontend panel registry still renders only statically known panel ids. This ADR
does not enable third-party frontend code loading, dynamic component import,
gateway routes, watchers, governance policies, marketplace behavior,
OS/container/WASM sandboxing, or production maturity.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python 3.10+; existing Slot Platform contracts; Vue static panel registry |
| **Domain** | Slot Platform UI metadata provider facet |
| **Knowledge Risk** | MEDIUM - provider import remains in-process, but UI output is static metadata filtered by existing backend/frontend registries |
| **References Consulted** | `docs/reference/python/VERSION.md`, `docs/architecture/adr-0053-ui-slot-consumer.md`, `docs/architecture/adr-0064-slot-provider-execution.md`, `docs/architecture/adr-0065-provider-package-identity.md`, `docs/architecture/adr-0068-slot-eval-suite-provider-facet.md`, `design/cdd/sprint-044-ui-slot-consumer.md`, `web/src/views/panelRegistry.ts`, `C:\Users\WSMAN\.claude\plans\openclaw-rippling-sparkle.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | provider execution UI facet tests, UI panel registry tests, slot API/CLI regression, governance validators, whitespace checks |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0043 (Slot Contribution Facets), ADR-0053 (UI Slot Consumer), ADR-0064 (Slot Provider Execution), ADR-0065 (Provider Package Identity), ADR-0066 (Code-String Isolation Prototype), ADR-0067 (Install Surfaces), ADR-0068 (Eval Suite Provider Facet) |
| **Extends** | ADR-0064 by moving only `ui_panels` from restricted provider facets into the installed-provider allowlist |
| **Supersedes** | ADR-0064's "UI panels are not executable from installed third-party providers" statement, only for metadata-only UI panel contributions |
| **Enables** | ADR-0070 watcher provider facet, then later governance policy and route facet decisions |
| **Blocks** | Any claim that P10 enables third-party frontend code loading, route injection, watchers, governance policy mutation, provider sandboxing, external gate closure, or production maturity |

## Context

ADR-0053 already introduced a conservative UI slot consumer: `UIPanelRegistry`,
`GET /v1/ui-panels`, and a frontend `panelRegistry.ts`. That path is
metadata-first. It does not dynamically import components from backend-provided
strings; the frontend normalizes remote metadata against a static list of known
Research workspace panel ids and zones.

That makes `ui_panels` the next lowest-risk P10 facet after eval suites. The
provider import risk remains the same ADR-0064 in-process provider risk, but
the output does not mount new HTTP routes, subscribe to runtime events, or
change entitlement/governance policy.

## Constraints

- Keep all provider execution gates from ADR-0064/0065.
- Require the existing `slot_ui` feature flag for UI slot resolution.
- Allow only `SlotType.UI` providers to contribute `ui_panels`.
- Keep `routes`, `watchers`, and `governance_policies` restricted.
- Do not load frontend code from provider packages or backend metadata.
- Keep the frontend panel registry static and allowlisted.
- Keep `production_ready: false`, `stable_declaration: forbidden`, and
  `level_3_sdk_platform: experimental`.

## Decision

`InstalledProviderSlot` now treats `SlotType.UI` as provider-executable and maps
it to the single allowed contribution field `ui_panels`.

Contribution validation still rejects:

- any route contribution;
- any watcher contribution;
- any governance policy contribution;
- any contribution field that belongs to a different slot type.

The existing `build_slot_aware_ui_panels()` factory continues to consume UI
panel contributions through `SlotKernel.resolve_contributions(...,
slot_type=SlotType.UI)`. `UIPanelRegistry` serializes metadata for API/Web
consumers. Frontend rendering remains controlled by the static
`panelRegistry.ts` allowlist.

## Alternatives Considered

### Alternative 1: Keep UI panels restricted

- **Pros**: No new provider facet surface.
- **Cons**: Prevents provider packages from contributing UI metadata that the
  current static frontend can safely ignore or normalize.
- **Rejection Reason**: Metadata-only UI panels can be opened without dynamic
  frontend code loading.

### Alternative 2: Dynamically load provider frontend components

- **Pros**: More plugin-like.
- **Cons**: Requires frontend package distribution, bundling, integrity,
  dependency, and sandbox policy decisions.
- **Rejection Reason**: This ADR is only about static metadata, not third-party
  frontend code execution.

### Alternative 3: Open UI panels together with routes

- **Pros**: More complete extension surface.
- **Cons**: Route injection is a larger in-process attack surface and must stay
  last in the P10 order.
- **Rejection Reason**: P10 requires one facet at a time.

## Consequences

### Positive

- Signed local providers can contribute UI panel metadata through the governed
  provider path.
- The frontend remains protected by static panel id/zone filtering.
- Routes, watchers, and governance policies remain closed.

### Negative

- Provider import still executes in-process when default-off provider gates are
  enabled.
- Unknown provider panel ids may appear in backend metadata but are ignored by
  the current frontend registry.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| UI panel metadata is mistaken for third-party frontend code loading | MEDIUM | HIGH | ADR/CDD/evidence state static metadata only; frontend allowlist remains the render authority. |
| Provider panel ids collide with built-ins | LOW | MEDIUM | Existing `UIPanelRegistry` duplicate checks fail fast within each workspace. |
| Remaining restricted facets open accidentally | LOW | HIGH | Tests keep route facets rejected after UI facet expansion; `_RESTRICTED_FACETS` still blocks routes/governance after ADR-0070. |

## CDD Requirements Addressed

| CDD System | Requirement | How This ADR Addresses It |
|------------|-------------|--------------------------|
| `design/cdd/p10-ui-panel-provider-facet.md` | Allow static UI panel metadata from installed signed providers. | Opens only `ui_panels` for provider execution, behind existing flags and trust gates. |
| `design/cdd/sprint-044-ui-slot-consumer.md` | UI panels resolve through `UIPanelRegistry` and static frontend rendering. | Reuses the existing backend registry and keeps dynamic component loading out of scope. |
| `design/cdd/p5-slot-provider-execution.md` | Restricted facets must fail closed unless a later ADR accepts one. | Supersedes only the UI panel restriction and keeps route/watcher/governance restrictions. |

## Validation Criteria

- Installed signed UI provider resolves through `build_slot_aware_ui_panels`.
- Provider panel rows serialize as metadata and include expected mode labels.
- UI registry tests still pass.
- Route facets remain rejected after UI expansion.
- Slot API/CLI regression passes.
- Governance validators pass and maturity posture remains unchanged.

## Related Decisions

- [ADR-0053: UI Slot Consumer](adr-0053-ui-slot-consumer.md)
- [ADR-0064: Slot Provider Execution](adr-0064-slot-provider-execution.md)
- [ADR-0065: Provider Package Identity](adr-0065-provider-package-identity.md)
- [ADR-0068: Slot Eval Suite Provider Facet](adr-0068-slot-eval-suite-provider-facet.md)
