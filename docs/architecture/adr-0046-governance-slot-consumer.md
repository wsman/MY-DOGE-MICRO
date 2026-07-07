# ADR-0046: Governance Slot Consumer

## Status

Accepted

## Date

2026-07-07

## Decision Makers

wsman (product owner) / implementation agent

## Summary

Sprint 037 consumes the `governance` slot facet at the existing tool-registry
entitlement seam. The built-in `governance.tool_policy` slot contributes the
default tool entitlement and high-risk approval policy, and the slot-aware tool
registry composes governance-policy checkers behind
`DOGE_FEATURE_SLOT_PLATFORM` + `DOGE_FEATURE_SLOT_GOVERNANCE`.

The flag-on default policy is parity-equivalent with the current
`ToolRegistry` defaults: forbidden tools remain hidden/blocked and high-risk
tools continue to require approval. Additional governance slots can constrain
the schema and execution surface through the same composition chain.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python 3.10+; existing `ToolRegistry`; existing slot facet dataclasses |
| **Domain** | Governance & Evaluation, tool entitlement and approval-policy composition |
| **Knowledge Risk** | LOW - local code path over existing protocols and dataclasses |
| **References Consulted** | `docs/architecture/adr-0013-tool-governance.md`, `docs/architecture/adr-0042-slot-platform.md`, `docs/architecture/adr-0043-slot-contribution-facets.md`, `docs/architecture/adr-0045-slot-discovery-surfaces.md`, `src/doge/application/tools/registry.py`, `src/doge/platform/slots/facets.py`, `C:\Users\WSMAN\.claude\plans\openclaw-like-magical-barto.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | governance slot unit tests, governance parity tests, tool-registry parity, CLI/API/doged slot status tests, settings/capability tests, import boundaries, docs validators, maturity honesty, plan closure, whitespace checks |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0013 (Financial Tool Governance), ADR-0015 (Enterprise Identity and Access Boundary), ADR-0019 (Capability Registry), ADR-0042 (Slot Platform Foundation), ADR-0043 (Slot Contribution Facets), ADR-0045 (Slot Discovery Surfaces) |
| **Extends** | ADR-0043 by adding a runtime consumer for the `governance_policies` facet |
| **Supersedes** | None |
| **Enables** | Watcher slots, later SlotPolicy consolidation, runtime permission enforcement, and enterprise allowlist policy composition |
| **Blocks** | None |

## Context

The Slot Platform roadmap requires every facet to become a controlled runtime
contribution point. Before this sprint, `GovernancePolicyContribution` existed
as a typed slot facet, but no runtime consumer used it. Tool entitlement and
high-risk approval decisions still lived entirely inside the `ToolRegistry`
default checker or a directly injected checker.

Governance is safety-sensitive because tool schema redaction and tool execution
checks run on the per-tool-call hot path. The first consumer must therefore be
feature-flagged, parity-tested, and limited to the existing tool entitlement
contract instead of introducing a broader policy engine.

## Constraints

- Keep `DOGE_FEATURE_SLOT_PLATFORM` and `DOGE_FEATURE_SLOT_GOVERNANCE` default
  `false`.
- Preserve flag-off tool-registry behavior byte-for-byte.
- Make the built-in governance slot parity-equivalent with the current default
  `ToolRegistry` policy when both slot flags are on.
- Compose explicit injected entitlement checkers with slot-contributed checkers.
- Fail fast on duplicate governance policy IDs.
- Do not add persistence, bundle activation, Web Slot Center, SDK slot client,
  external auth changes, watcher middleware, lifecycle invocation, or runtime
  permission/health enforcement.
- Do not close external/operator gates or change production maturity posture.

## Decision

Add `src/doge/platform/governance/slot.py` with three concrete pieces:

- `ToolGovernancePolicySlot`, the built-in governance slot.
- `DefaultToolGovernanceChecker`, the slot-contributed equivalent of the
  current `ToolRegistry` default entitlement behavior.
- `CompositeToolEntitlementChecker`, an AND/OR composition helper:
  - `can_execute` is allowed only when all checkers allow.
  - `requires_approval` is true when any checker requires approval.
  - `redact_schema` pipes the schema through each checker and hides it if any
    checker returns `None`.

Register `ToolGovernancePolicySlot` in the built-in slot registry.

Add `build_slot_aware_entitlement_checker()` in
`src/doge/bootstrap/runtime_factories/slots.py`. It resolves only governance
slots whose feature flags are satisfied, collects
`GovernancePolicyContribution.entitlement_checker_factory`, rejects duplicate
policy IDs, and returns:

- the caller-supplied checker unchanged when no governance slot checker is
  active,
- the single active checker when exactly one checker exists, or
- `CompositeToolEntitlementChecker` when multiple checkers are active.

Update `build_slot_aware_tool_registry()` to pass the effective entitlement
checker into `ToolRegistry`. The existing tool contribution and remaining-tool
registration behavior is unchanged.

Add `DOGE_FEATURE_SLOT_GOVERNANCE` and lifecycle metadata, and expose
`feature.slot_platform` / `feature.slot_governance` through the capability
registry.

## Alternatives Considered

### Alternative 1: Replace `ToolRegistry` default policy immediately

- **Description**: Remove the private default checker from `ToolRegistry` and
  require the governance slot path for all registry construction.
- **Pros**: One source for entitlement behavior.
- **Cons**: High blast radius and no easy flag-off rollback.
- **Rejection Reason**: Governance is a hot path; the first slot consumer must
  be additive and reversible.

### Alternative 2: Build a general SlotPolicy engine now

- **Description**: Implement bundle-wide policy merging, precedence, mutation,
  persistence, and enterprise allowlist behavior.
- **Pros**: Closer to the final platform shape.
- **Cons**: Premature before several facet consumers exist and before
  `SlotKernel`/`SlotBundle` are first-class.
- **Rejection Reason**: Sprint 037 only needs the governance facet consumer at a
  real seam; broader policy orchestration belongs to the later SlotKernel wave.

### Alternative 3: Put approval-policy templates into workflow slots only

- **Description**: Keep high-risk tool policy in workflow metadata instead of
  adding a governance consumer.
- **Pros**: Reuses existing workflow-template policy fields.
- **Cons**: Tool entitlement is not always workflow-scoped and must apply to
  direct registry discovery/execution as well.
- **Rejection Reason**: The enforcement seam is the tool registry; workflow
  metadata is display/planning input, not sufficient runtime policy.

## Consequences

### Positive

- The `governance` facet now has a real runtime consumer.
- Built-in governance policy is visible as `governance.tool_policy`.
- Tool entitlement policy can be extended through slot contributions without
  modifying `ToolRegistry`.
- Duplicate governance policy IDs fail fast.
- Flag-on default behavior is parity-tested against the legacy path.

### Negative

- Governance composition is limited to tool entitlement and approval checks.
- The default `ToolRegistry` fallback still exists for flag-off and non-slot
  construction paths.
- There is still no SlotKernel, SlotPolicy persistence, permission enforcement,
  active health probing, watcher middleware, or third-party slot policy.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Slot governance changes tool schema discovery unexpectedly | LOW | HIGH | Parity tests compare schemas and capability records with the flag-off registry. |
| Additional checkers conflict silently | LOW | MEDIUM | Duplicate policy IDs raise `SlotConfigurationError`; composition is deterministic. |
| Approval metadata is dropped by restrictive checkers | LOW | MEDIUM | Composite approval is `any(checker.requires_approval(...))`; constrained tools are hidden/blocked consistently. |
| Operators mistake governance slot for full permission enforcement | LOW | MEDIUM | ADR/CDD/evidence keep permission/health enforcement out of scope and maturity experimental. |

## CDD Requirements Addressed

| CDD System | Requirement | How This ADR Addresses It |
|------------|-------------|--------------------------|
| `design/cdd/sprint-037-governance-slot-consumer.md` | Governance slots can contribute tool entitlement policy to the runtime tool registry. | Adds `governance.tool_policy` and `build_slot_aware_entitlement_checker()`. |
| `design/cdd/bc-08-governance-evaluation.md` | Governance owns entitlement and approval policy boundaries. | Places the built-in governance slot under `doge.platform.governance`. |
| `design/cdd/capability-registry.md` | Feature and capability discovery remain redacted and maturity-honest. | Exposes slot platform/governance feature capabilities without changing production posture. |

## Performance Implications

- **CPU**: one small entitlement-checker composition chain on tool schema and
  execution paths when slot governance is enabled.
- **Memory**: negligible; stores a tuple of checker instances.
- **Load Time**: imports one platform governance module into the built-in slot
  registry.
- **Network**: none.

## Migration Plan

1. Add the built-in governance slot and checker implementations.
2. Register the slot in the built-in registry.
3. Add `build_slot_aware_entitlement_checker()`.
4. Wire the composed checker into `build_slot_aware_tool_registry()`.
5. Add `DOGE_FEATURE_SLOT_GOVERNANCE` and capability discovery rows.
6. Add focused unit/parity/API/CLI/doged tests.
7. Keep broader SlotPolicy, watcher, bundle, permission enforcement, Web, SDK,
   and third-party work deferred.

## Validation Criteria

- `governance.tool_policy` manifest is typed as `governance`, declares
  `slot_platform` + `slot_governance`, and provides `tool_entitlement` plus
  `approval_policy`.
- With slot governance on, built-in tool schemas and capability records match
  the flag-off tool-registry baseline.
- High-risk tools still surface `approval_required`.
- A custom governance policy can hide/block high-risk tools while preserving
  allowed read-only tools.
- Duplicate governance policy IDs fail fast.
- CLI/API/doged slot discovery lists `governance.tool_policy` disabled until
  `DOGE_FEATURE_SLOT_GOVERNANCE=1`.
- Maturity posture remains `production_ready: false`,
  `stable_declaration: forbidden`, and `level_3_sdk_platform: experimental`.

## Related Decisions

- ADR-0013: Financial Tool Governance
- ADR-0015: Enterprise Identity and Access Boundary
- ADR-0019: Capability Registry
- ADR-0042: Slot Platform Foundation
- ADR-0043: Slot Contribution Facets
- ADR-0045: Slot Discovery Surfaces
