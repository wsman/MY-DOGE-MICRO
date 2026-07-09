# ADR-0068: Slot Eval Suite Provider Facet

## Status

Accepted

## Date

2026-07-09

## Decision Makers

wsman (product owner) / implementation agent

## Summary

P10 opens the first previously restricted installed-provider facet:
`eval_suites`. Installed third-party providers may now contribute eval suites
when they pass the existing ADR-0064/0065 provider execution chain:
installed slot, `slot_install`, `slot_runtime_interception`,
`slot_provider_execution`, v3 package-aware signature, revocation check,
enterprise allowlist when applicable, and SlotKernel admission.

This ADR does not open gateway routes, UI panels, watchers, or governance
policies. It does not add marketplace behavior, YAML manifests, URL/upload
install, OS/container/WASM sandboxing, transitive dependency signing, or
production maturity.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python 3.10+; existing Slot Platform contracts; pytest |
| **Domain** | Slot Platform provider facet expansion |
| **Knowledge Risk** | MEDIUM - provider code still imports in-process, but eval suite contributions are declarative records consumed by the existing offline eval registry |
| **References Consulted** | `docs/reference/python/VERSION.md`, `docs/architecture/adr-0064-slot-provider-execution.md`, `docs/architecture/adr-0065-provider-package-identity.md`, `docs/architecture/adr-0066-code-string-isolation-prototype.md`, `docs/architecture/adr-0067-slot-install-surfaces.md`, `design/cdd/sprint-042-eval-slot-consumer.md`, `C:\Users\WSMAN\.claude\plans\openclaw-rippling-sparkle.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | provider execution regression tests, eval suite registry tests, slot API/CLI regression, governance validators, whitespace checks |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0043 (Slot Contribution Facets), ADR-0051 (Eval Slot Consumer), ADR-0064 (Slot Provider Execution), ADR-0065 (Provider Package Identity), ADR-0066 (Code-String Isolation Prototype), ADR-0067 (Install Surfaces) |
| **Extends** | ADR-0064 by moving only `eval_suites` from restricted provider facets into the installed-provider allowlist |
| **Supersedes** | ADR-0064's "eval suites are not executable from installed third-party providers" statement, only for the default-off local alpha provider path |
| **Enables** | Later restricted facet expansion for UI panels, watchers, governance policies, and routes |
| **Blocks** | Any claim that P10 opens routes/UI/watchers/governance provider facets, enables marketplace install, provides provider sandboxing, closes external gates, or changes production maturity |

## Context

ADR-0064 intentionally limited installed-provider execution to lower-risk
facets: tools, model backends, workflows, data sources, and document parsers.
It rejected gateway routes, UI panels, watchers, eval suites, and governance
policies as restricted facets until each could be evaluated independently.

Eval suites are the lowest-risk remaining facet because the contribution shape
is a declarative `EvalSuiteContribution`: suite id, local cases path,
execution profile, and policy labels. The existing `EvalSuiteRegistry` validates
duplicate suite ids and missing cases paths before the offline runner uses a
suite. Opening this facet does not introduce HTTP route mounting, frontend code
loading, runtime event hooks, or entitlement policy mutation.

## Constraints

- Keep all provider execution gates from ADR-0064/0065.
- Keep provider import in bootstrap-owned `InstalledProviderSlot`, not
  `SlotLoader`.
- Allow only `SlotType.EVAL` providers to contribute `eval_suites`.
- Keep `routes`, `ui_panels`, `watchers`, and `governance_policies`
  restricted.
- Keep P8's provider contribution residual unchanged: provider code is still
  in-process and not OS/container/WASM isolated.
- Keep `production_ready: false`, `stable_declaration: forbidden`, and
  `level_3_sdk_platform: experimental`.

## Decision

`InstalledProviderSlot` now treats `SlotType.EVAL` as provider-executable and
maps it to the single allowed contribution field `eval_suites`.

Contribution validation still rejects:

- any route contribution;
- any UI panel contribution;
- any watcher contribution;
- any governance policy contribution;
- any contribution field that belongs to a different slot type.

The existing `build_slot_aware_eval_suites()` factory continues to consume eval
suite contributions through `SlotKernel.resolve_contributions(...,
slot_type=SlotType.EVAL)`. That means installed eval providers remain subject to
SlotKernel policy, active bundle policy, enforcement, and admission status.

## Alternatives Considered

### Alternative 1: Keep eval suites restricted

- **Pros**: No new provider facet surface.
- **Cons**: Prevents signed local eval suite packs from using the installed
  provider path.
- **Rejection Reason**: Eval suites are declarative enough to open first under
  the existing provider gates.

### Alternative 2: Open all remaining restricted facets

- **Pros**: Faster path toward a broad plugin ecosystem.
- **Cons**: Routes, UI panels, watchers, and governance policies have distinct
  escalation and in-process attack surfaces.
- **Rejection Reason**: P10 explicitly requires one facet at a time, with routes
  last.

### Alternative 3: Add a new eval-specific install/execution flag

- **Pros**: More granular operator control.
- **Cons**: Adds flag complexity while the provider path is already default-off
  and gated by signature, revocation, allowlist, runtime interception, and
  SlotKernel admission.
- **Rejection Reason**: Use the existing provider gate until a real operational
  need for per-facet flags appears.

## Consequences

### Positive

- Signed local eval suite packs can be installed and discovered through the same
  governed provider path as other allowed facets.
- The first P10 facet expands capability without touching route mounting,
  frontend loading, runtime watcher hooks, or governance policy mutation.
- Tests now prove routes remain restricted after eval suite expansion.

### Negative

- Provider import still executes in-process when the default-off gates are
  enabled.
- Eval suite paths are local filesystem paths; this is not a remote marketplace
  or registry model.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Operators read eval suite providers as sandboxed plugin execution | MEDIUM | HIGH | ADR/CDD/evidence repeat that provider code remains in-process and P8 does not isolate provider objects. |
| Eval cases path points at unintended local files | MEDIUM | MEDIUM | Existing `EvalSuiteRegistry` validates path existence; provider execution remains trusted-publisher/operator-gated. |
| Remaining restricted facets open accidentally | LOW | HIGH | Tests assert route facets remain rejected after P10 eval expansion; `_RESTRICTED_FACETS` still blocks routes/UI/watchers/governance. |

## CDD Requirements Addressed

| CDD System | Requirement | How This ADR Addresses It |
|------------|-------------|--------------------------|
| `design/cdd/p10-eval-suite-provider-facet.md` | Allow the first restricted provider facet in a narrow, audited way. | Opens only `eval_suites` for installed, signed, operator-gated providers. |
| `design/cdd/p5-slot-provider-execution.md` | Restricted facets must fail closed unless a later ADR accepts one. | Supersedes only the eval suite restriction and keeps route/UI/watcher/governance restrictions. |
| `design/cdd/sprint-042-eval-slot-consumer.md` | Eval suite contributions resolve through `EvalSuiteRegistry`. | Reuses the existing `build_slot_aware_eval_suites()` path. |

## Validation Criteria

- Installed signed eval provider resolves through `build_slot_aware_eval_suites`.
- Provider eval suite registry record exposes the expected cases path,
  execution profile, and eval policy labels.
- Provider import does not happen from status discovery alone.
- Route facets remain rejected after P10 eval expansion.
- Focused provider/eval tests pass.
- Governance validators pass and maturity posture remains unchanged.

## Related Decisions

- [ADR-0043: Slot Contribution Facets](adr-0043-slot-contribution-facets.md)
- [ADR-0051: Eval Slot Consumer](adr-0051-eval-slot-consumer.md)
- [ADR-0064: Slot Provider Execution](adr-0064-slot-provider-execution.md)
- [ADR-0065: Provider Package Identity](adr-0065-provider-package-identity.md)
- [ADR-0066: Code-String Isolation Prototype](adr-0066-code-string-isolation-prototype.md)
- [ADR-0067: Slot Install Surfaces](adr-0067-slot-install-surfaces.md)
