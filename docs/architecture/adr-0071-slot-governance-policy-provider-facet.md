# ADR-0071: Slot Governance Policy Provider Facet

## Status

Accepted

## Date

2026-07-09

## Decision Makers

wsman (product owner) / implementation agent

## Summary

P10 opens the fourth previously restricted installed-provider facet:
`governance_policies`. Installed third-party providers may now contribute tool
entitlement governance policies when they pass the existing ADR-0064/0065
provider execution chain and when `DOGE_FEATURE_SLOT_GOVERNANCE` is enabled.

Governance policy providers are constrained to the existing tool entitlement
composition seam. The composite checker can only make `can_execute` stricter
(`all(...)`) and `requires_approval` stricter (`any(...)`), so provider
policies cannot override the built-in forbidden-tool deny rule or remove the
built-in high-risk approval requirement.

Provider checker factories and checker method calls run inside the slot
permission context when runtime interception is enabled. This ADR does not open
gateway routes. It does not add marketplace behavior, YAML manifests,
URL/upload install, OS/container/WASM sandboxing, transitive dependency
signing, provider malicious-code containment, tenant-isolation expansion, or
production maturity.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python 3.10+; existing Slot Platform contracts and tool entitlement checker composition |
| **Domain** | Slot Platform governance policy provider facet |
| **Knowledge Risk** | HIGH - governance policies participate in tool entitlement decisions and still execute in-process |
| **References Consulted** | `docs/reference/python/VERSION.md`, `docs/architecture/adr-0046-governance-slot-consumer.md`, `docs/architecture/adr-0064-slot-provider-execution.md`, `docs/architecture/adr-0065-provider-package-identity.md`, `docs/architecture/adr-0070-slot-watcher-provider-facet.md`, `design/cdd/sprint-037-governance-slot-consumer.md`, `C:\Users\WSMAN\.claude\plans\openclaw-rippling-sparkle.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | provider governance tests, governance slot parity tests, slot API/CLI regression, governance validators, whitespace checks |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0043 (Slot Contribution Facets), ADR-0046 (Governance Slot Consumer), ADR-0064 (Slot Provider Execution), ADR-0065 (Provider Package Identity), ADR-0066 (Code-String Isolation Prototype), ADR-0067 (Install Surfaces), ADR-0068 (Eval Suite Provider Facet), ADR-0069 (UI Panel Provider Facet), ADR-0070 (Watcher Provider Facet) |
| **Extends** | ADR-0064 by moving only `governance_policies` from restricted provider facets into the installed-provider allowlist |
| **Supersedes** | ADR-0064's "governance policies are not executable from installed third-party providers" statement, only for the default-off local provider path |
| **Enables** | Later route facet decision |
| **Blocks** | Any claim that P10 enables route injection, provider sandboxing, tenant-isolation expansion, external gate closure, or production maturity |

## Context

ADR-0046 already introduced a built-in governance slot consumer at the tool
registry entitlement seam. It composes `can_execute`, `requires_approval`, and
`redact_schema` through `CompositeToolEntitlementChecker`.

Opening governance policy providers is riskier than eval/UI metadata and
watcher observation because provider code participates in authorization-like
decisions. P10 therefore keeps all ADR-0064/0065 gates, requires the existing
`slot_governance` flag, preserves monotonic checker composition, and wraps
provider factories and checker methods in the slot permission context.

## Constraints

- Keep all provider execution gates from ADR-0064/0065.
- Require the existing `slot_governance` feature flag for governance policy
  resolution.
- Allow only `SlotType.GOVERNANCE` providers to contribute
  `governance_policies`.
- Keep `routes` restricted.
- Preserve monotonic entitlement composition: provider policies can deny or
  require more approval, but cannot grant forbidden tools or remove high-risk
  approval.
- Execute provider policy factories and checker methods with active slot
  permission context when runtime interception is enabled.
- Keep tenant isolation unchanged; this facet does not introduce cross-tenant
  policy grants or production authorization semantics.
- Keep `production_ready: false`, `stable_declaration: forbidden`, and
  `level_3_sdk_platform: experimental`.

## Decision

`InstalledProviderSlot` now treats `SlotType.GOVERNANCE` as
provider-executable and maps it to the single allowed contribution field
`governance_policies`.

`build_slot_aware_entitlement_checker()` now wraps provider governance policy
factory calls and returned checker methods in slot scope when runtime
interception is enabled:

```text
InstalledProviderSlot
  -> SlotKernel.resolve_contributions(slot_type=SlotType.GOVERNANCE)
  -> build_slot_aware_entitlement_checker()
  -> CompositeToolEntitlementChecker
```

Contribution validation still rejects:

- any route contribution;
- any contribution field that belongs to a different slot type.

## Alternatives Considered

### Alternative 1: Keep governance policies restricted

- **Pros**: Avoids expanding an authorization-like in-process seam.
- **Cons**: Prevents signed local providers from contributing stricter local
  tool entitlement policy.
- **Rejection Reason**: Existing composition is monotonic and can keep provider
  policies from widening built-in entitlement decisions.

### Alternative 2: Allow provider policies to replace the composite checker

- **Pros**: More flexible extension behavior.
- **Cons**: Could remove built-in forbidden-tool denial or high-risk approval.
- **Rejection Reason**: P10 requires additive, restrictive policy contribution
  only.

### Alternative 3: Open routes together with governance policies

- **Pros**: Completes restricted facet expansion in one step.
- **Cons**: FastAPI route injection is the broadest in-process attack surface.
- **Rejection Reason**: P10 requires `routes` last and separately validated.

## Consequences

### Positive

- Signed local providers can contribute stricter tool entitlement policy through
  the governed provider path.
- Provider governance checker execution now carries slot permission context.
- Built-in forbidden-tool denial and high-risk approval behavior remain in
  force through monotonic composition.

### Negative

- Provider governance code still runs in-process when default-off gates are
  enabled.
- A provider policy can intentionally restrict or require more approval for
  tools once installed and enabled by the operator.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Provider policy over-restricts local tool access | MEDIUM | MEDIUM | Provider execution is default-off/operator-gated; policy composition is explicit and tested. |
| Provider policy attempts to widen entitlement | LOW | HIGH | Composite `can_execute=all(...)` and `requires_approval=any(...)` preserve built-in denials and approvals. |
| Remaining route facet opens accidentally | LOW | HIGH | Tests keep route facets rejected after governance expansion; `_RESTRICTED_FACETS` still blocks routes. |

## CDD Requirements Addressed

| CDD System | Requirement | How This ADR Addresses It |
|------------|-------------|--------------------------|
| `design/cdd/p10-governance-policy-provider-facet.md` | Allow governance policy provider facets only through monotonic entitlement composition and slot scope. | Opens only `governance_policies`, wraps factory/checker execution in slot permission context, and keeps route facets restricted. |
| `design/cdd/sprint-037-governance-slot-consumer.md` | Governance slots compose tool entitlement checks at the ToolRegistry seam. | Reuses `build_slot_aware_entitlement_checker()` and `CompositeToolEntitlementChecker`. |
| `design/cdd/p5-slot-provider-execution.md` | Restricted facets must fail closed unless a later ADR accepts one. | Supersedes only the governance policy restriction and keeps route restrictions. |

## Validation Criteria

- Installed signed governance provider resolves through
  `build_slot_aware_entitlement_checker()`.
- Provider governance checker methods run with active slot permission context.
- Built-in governance parity tests still pass.
- Forbidden tools cannot be re-enabled by a provider governance policy.
- Route facets remain rejected after governance expansion.
- Slot API/CLI regression passes.
- Governance validators pass and maturity posture remains unchanged.

## Related Decisions

- [ADR-0046: Governance Slot Consumer](adr-0046-governance-slot-consumer.md)
- [ADR-0064: Slot Provider Execution](adr-0064-slot-provider-execution.md)
- [ADR-0065: Provider Package Identity](adr-0065-provider-package-identity.md)
- [ADR-0070: Slot Watcher Provider Facet](adr-0070-slot-watcher-provider-facet.md)
