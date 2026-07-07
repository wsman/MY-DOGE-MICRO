# Sprint 037 CDD: Governance Slot Consumer

Status: Ready for Acceptance
Date: 2026-07-07

## 1. Overview

Sprint 037 makes the Slot Platform consume the `governance` facet for tool
entitlement and approval-policy composition.

The sprint adds a built-in `governance.tool_policy` slot, composes
slot-contributed entitlement checkers into the slot-aware `ToolRegistry`, and
keeps all behavior behind `DOGE_FEATURE_SLOT_PLATFORM` plus
`DOGE_FEATURE_SLOT_GOVERNANCE`.

The sprint does not implement a full SlotKernel, SlotPolicy engine, runtime
permission enforcement, or third-party slot governance.

## 2. User Promise / JTBD

A platform engineer can see governance as a real slot contribution and can wire
additional governance policies into tool schema redaction and execution checks
without editing `ToolRegistry` internals.

A local operator can inspect `governance.tool_policy` through existing slot
discovery surfaces and see whether its feature flags are satisfied.

## 3. Detailed Behavior

- `ToolGovernancePolicySlot` lives in `doge.platform.governance.slot`.
- The slot manifest:
  - uses id `governance.tool_policy`
  - uses type `governance`
  - declares feature flags `slot_platform` and `slot_governance`
  - declares capabilities `tool_entitlement` and `approval_policy`
  - declares low risk and no filesystem/network/shell/database/secrets access
- `ToolGovernancePolicySlot.resolve()` returns one
  `GovernancePolicyContribution` with an entitlement checker factory.
- `DefaultToolGovernanceChecker` mirrors the current `ToolRegistry` default:
  - forbidden tools cannot execute and are hidden from schemas
  - high-risk tools require approval
- `CompositeToolEntitlementChecker` composes multiple checkers:
  - all checkers must allow execution
  - any checker can require approval
  - schema redaction is applied in order and stops at `None`
- `build_slot_aware_entitlement_checker()` resolves governance slots only when
  their feature flags are on.
- Duplicate governance policy IDs raise `SlotConfigurationError`.
- `build_slot_aware_tool_registry()` uses the effective composed checker.
- `FeatureCapabilityProvider` exposes `feature.slot_platform` and
  `feature.slot_governance` lifecycle metadata.
- CLI/API/doged slot discovery shows `governance.tool_policy` as disabled until
  both slot feature flags are satisfied.

## 4. Contracts / Data Model

Governance policy contribution:

```python
GovernancePolicyContribution(
    policy_id="governance.tool_policy.default_entitlement",
    kind="tool_entitlement",
    payload={
        "blocked_categories": ("forbidden",),
        "approval_required_categories": ("high_risk",),
    },
    entitlement_checker_factory=...,
)
```

Checker protocol:

```python
can_execute(context, tool_name, category) -> bool
requires_approval(context, tool_name, category) -> bool
redact_schema(context, schema, category) -> dict | None
```

Feature flags:

```text
DOGE_FEATURE_SLOT_PLATFORM=1
DOGE_FEATURE_SLOT_GOVERNANCE=1
```

## 5. Edge Cases

- Slot platform off: no slot-aware tool-registry path is selected by the public
  factory; slot discovery reports disabled status.
- Slot platform on but slot governance off: the governance slot is registered
  but not resolved; the tool registry keeps existing behavior.
- Slot governance on with only the built-in policy: schemas, capability
  records, approval metadata, and execution decisions match the flag-off path.
- Custom restrictive governance policy: disallowed tools are hidden from schema
  discovery and return `tool not permitted` on execution.
- Duplicate governance policy ID: construction fails before tool registry use.

## 6. Dependencies

- ADR-0013 Financial Tool Governance.
- ADR-0042 Slot Platform Foundation.
- ADR-0043 Slot Contribution Facets.
- ADR-0045 Slot Discovery Surfaces.
- Existing `ToolRegistry` entitlement checker protocol.
- Existing `GovernancePolicyContribution` facet.

## 7. Configuration Knobs

- `DOGE_FEATURE_SLOT_PLATFORM`: default `false`; gates slot-aware tool registry
  and slot discovery.
- `DOGE_FEATURE_SLOT_GOVERNANCE`: default `false`; gates governance-policy slot
  resolution.

Both flags remain off by default.

## 8. Acceptance Criteria

- Built-in registry includes `governance.tool_policy`.
- Governance slot manifest/status is visible through `doge slots`, `doged
  slots`, and `/v1/slots`.
- Governance slot remains disabled unless both slot flags are on.
- Slot-aware tool registry composes governance checkers when enabled.
- Built-in governance checker is parity-equivalent with the flag-off tool
  registry.
- Custom governance checker can constrain schemas and execution.
- Duplicate governance policy IDs fail fast.
- Capability registry exposes slot platform/governance feature lifecycle
  metadata.
- No Web Slot Center, SDK slot client, persistence schema, external auth,
  watcher middleware, SlotKernel, SlotBundle, SlotPolicy, SlotLoader, lifecycle
  invocation, permission/health enforcement, third-party install, signing, or
  enterprise allowlist is added.
- Maturity posture remains `production_ready: false`,
  `stable_declaration: forbidden`, and `level_3_sdk_platform: experimental`.

## 9. Validation Plan

```bash
py -3 -m pytest tests/unit/platform/slots/test_builtin_governance_slot.py tests/contract/test_governance_slot_parity.py tests/contract/test_tool_registry_slot_parity.py tests/cli/test_cli_slots.py tests/contract/test_slot_api.py tests/cli/test_doged_cli.py tests/test_settings.py tests/unit/use_cases/test_capability_registry.py -q
py -3 -m pytest tests/unit/platform/slots tests/contract/test_workflow_slot_parity.py tests/contract/test_agent_backends_slot_parity.py tests/contract/test_tool_registry_slot_parity.py tests/contract/test_governance_slot_parity.py -q
py -3 tools/ci/sdk-contract-check.py
py -3 scripts/validate_import_boundaries.py
py -3 scripts/validate_docs_authority.py
py -3 scripts/validate_docs_links.py
py -3 scripts/validate_docs_maturity_claims.py
py -3 scripts/validate_alpha_maturity_honesty.py --file docs/architecture/adr-0046-governance-slot-consumer.md
py -3 scripts/validate_alpha_maturity_honesty.py --file design/cdd/sprint-037-governance-slot-consumer.md
py -3 scripts/validate_no_stale_counts.py
py -3 scripts/validate_adr_index_completeness.py
py -3 scripts/validate_governance_yaml_shape.py
py -3 scripts/validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/openclaw-like-magical-barto.md
git diff --check
cmd.exe /c git diff --check
```

## 10. Local Verification Result

Final local verification is recorded in
`production/qa/evidence/sprint-037-governance-slot-consumer-manifest.md`.

## 11. Out of Scope

- `SlotKernel`, `SlotLifecycle`, `SlotBundle`, `SlotPolicy`, and `SlotLoader`.
- Runtime permission/health enforcement and active health probes.
- Watcher slots or runtime event middleware.
- `/v1/slot-bundles`, bundle activation, YAML manifests, third-party install,
  signing, or enterprise allowlist.
- Web Slot Center or SDK slot client source.
- Persistence schema, ModelRouter/ProfileRegistry, runtime dispatch, external
  auth, or worker behavior changes.
- Production readiness declaration or external/operator gate closure.
