# Sprint 043 CDD: Slot Kernel, Bundles, Policy, and Lifecycle

Status: Ready for Acceptance
Date: 2026-07-07

## 1. Overview

Sprint 043 makes the Slot Platform orchestration layer first-class.

The sprint adds pure contracts for `SlotKernel`, `SlotPolicy`, `SlotBundle`, and
`SlotLifecycle`; refactors existing slot-aware consumers to resolve through the
kernel; and exposes read-only built-in bundle status through `/v1/slot-bundles`.

The sprint does not add activation, persistent enable/disable state, disk
manifest loading, third-party install, signing, Web Slot Center, SDK slot
client, runtime permission enforcement, or active health probes.

## 2. User Promise / JTBD

A platform engineer can inspect one kernel-backed view of built-in slots and
scenario bundles instead of reasoning about many independent registry scans.

An operator can see which built-in bundles are fully resolved, partially
resolved, or disabled by current feature flags before later activation work
exists.

## 3. Detailed Behavior

- `SlotPolicy` lives in `doge.platform.slots.policy`.
- `SlotPolicy` supports explicit enabled slots, explicit disabled slots, and
  feature-flag enforcement.
- Disabled slots win over enabled slots.
- `SlotBundle` and `SlotBundleStatus` live in `doge.platform.slots.bundles`.
- Bundle IDs must start with `bundle.`.
- Bundles must include at least one slot.
- Bundle enabled/disabled overlap is rejected.
- `SlotLifecycle` lives in `doge.platform.slots.lifecycle`.
- Lifecycle invokes `ISlot.start()` once per kernel instance and `ISlot.stop()`
  in reverse start order.
- `SlotKernel` lives in `doge.platform.slots.kernel`.
- `SlotKernel` wraps `SlotRegistry`, `SlotPolicy`, `SlotLifecycle`, and bundle
  definitions.
- `SlotKernel.resolve_contributions(context, slot_type=...)` is the common
  resolver for all existing slot-aware consumers.
- `build_builtin_slot_kernel()` lives in
  `doge.bootstrap.runtime_factories.slots`.
- Existing slot-aware tool, model, workflow, governance, watcher, document,
  data, gateway, and eval helpers resolve contributions through the kernel.
- `build_slot_bundle_rows()` returns read-only built-in bundle rows.
- `/v1/slot-bundles` returns those rows when `DOGE_FEATURE_SLOT_PLATFORM=1`.
- Route authority is updated to 94 HTTP routes.

## 4. Contracts / Data Model

Kernel API:

```python
class SlotKernel:
    def status(self, context: SlotContext) -> tuple[SlotStatusRecord, ...]: ...
    def bundle_status(self, context: SlotContext) -> tuple[SlotBundleStatus, ...]: ...
    def resolve_contributions(
        self,
        context: SlotContext,
        *,
        slot_type: SlotType | None = None,
    ) -> tuple[SlotContribution, ...]: ...
    def start(self, context: SlotContext, *, slot_type: SlotType | None = None): ...
    def stop(self, context: SlotContext): ...
```

Read-only bundle route:

```http
GET /v1/slot-bundles
```

Response shape:

```json
{
  "bundles": [
    {
      "id": "bundle.local_analyst",
      "status": "partial",
      "slot_ids": ["market.core"],
      "enabled_slot_ids": ["market.core"],
      "disabled_slot_ids": ["workflow.templates"],
      "missing_slot_ids": [],
      "counts": {"slots": 9, "enabled": 6, "disabled": 3, "missing": 0}
    }
  ]
}
```

Feature flag:

```text
DOGE_FEATURE_SLOT_PLATFORM=1
```

No new feature flag is added for this sprint.

Maturity posture:

```yaml
production_ready: false
stable_declaration: forbidden
level_3_sdk_platform: experimental
```

## 5. Edge Cases

- Slot platform off: `/v1/slot-bundles` returns the same 404 gate as `/v1/slots`.
- Unknown bundle ID through the kernel raises `UnknownSlotError`.
- Bundle references to unknown slots are rejected by direct `SlotKernel`
  construction.
- Bootstrap filters built-in bundles to those supported by the current registry
  so focused tests with custom registries can still exercise duplicate
  contribution errors.
- Duplicate bundle IDs fail fast.
- Lifecycle start failures and stop failures surface as `SlotConfigurationError`.
- Bundle status is not persisted activation state.

## 6. Dependencies

- ADR-0042 Slot Platform Foundation.
- ADR-0043 Slot Contribution Facets.
- ADR-0045 Slot Discovery Surfaces.
- ADR-0051 Eval Slot Consumer.
- Existing built-in slot providers and slot-aware runtime factories.

## 7. Configuration Knobs

- `DOGE_FEATURE_SLOT_PLATFORM`: default `false`; gates slot discovery,
  bundle discovery, and slot-aware consumer paths.

No bundle activation or persistent policy configuration is added.

## 8. Acceptance Criteria

- `doge.platform.slots` exports `SlotKernel`, `SlotPolicy`, `SlotBundle`, and
  `SlotLifecycle` contracts.
- `doge.platform.slots` remains pure and passes import-boundary gates.
- Existing slot-aware consumers resolve through `SlotKernel`.
- Built-in bundles are discoverable through `build_slot_bundle_rows()`.
- `/v1/slot-bundles` returns read-only bundle status when slot platform is on.
- `/v1/slot-bundles` remains feature-gated when slot platform is off.
- Tool/model/workflow/governance/watcher/document/data/gateway/eval parity
  tests continue to pass.
- API route authority is synchronized at 94 HTTP routes.
- No bundle activation, disk loader, install, signing, SDK slot client, Web Slot
  Center, runtime permission enforcement, active health probe, production
  readiness declaration, or external/operator gate closure is added.

## 9. Validation Plan

```bash
py -3 -m pytest tests/unit/platform/slots/test_slot_policy.py tests/unit/platform/slots/test_slot_bundle.py tests/unit/platform/slots/test_slot_kernel.py tests/contract/test_slot_kernel_bundle_rows.py tests/contract/test_slot_api.py -q
py -3 -m pytest tests/unit/platform/slots tests/unit/eval tests/contract/test_tool_registry_slot_parity.py tests/contract/test_agent_backends_slot_parity.py tests/contract/test_workflow_slot_parity.py tests/contract/test_governance_slot_parity.py tests/contract/test_watcher_slot_parity.py tests/contract/test_document_slot_parity.py tests/contract/test_data_source_slot_parity.py tests/contract/test_gateway_slot_parity.py tests/contract/test_eval_slot_parity.py tests/contract/test_slot_kernel_bundle_rows.py tests/contract/test_slot_api.py tests/cli/test_cli_slots.py tests/cli/test_doged_cli.py -q
py -3 -m pytest tests/contract/test_api_doc_route_coverage.py tests/unit/governance/test_s017_planning_docs.py -q
py -3 -m pytest tests/unit/architecture/test_slot_boundary.py tests/unit/architecture/test_bootstrap_owns_factories.py -q
py -3 tools/ci/sdk-contract-check.py
py -3 scripts/validate_import_boundaries.py
py -3 scripts/validate_docs_authority.py
py -3 scripts/validate_docs_links.py
py -3 scripts/validate_docs_maturity_claims.py
py -3 scripts/validate_alpha_maturity_honesty.py --file docs/architecture/adr-0052-slot-kernel-bundles-policy.md
py -3 scripts/validate_alpha_maturity_honesty.py --file design/cdd/sprint-043-slot-kernel-bundles-policy.md
py -3 scripts/validate_no_stale_counts.py
py -3 scripts/validate_adr_index_completeness.py
py -3 scripts/validate_governance_yaml_shape.py
py -3 scripts/validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/openclaw-like-magical-barto.md
git diff --check
cmd.exe /c git diff --check
```

## 10. Local Verification Result

Final local verification is recorded in
`production/qa/evidence/sprint-043-slot-kernel-bundles-policy-manifest.md`.

## 11. Out of Scope

- Bundle activation and persistent policy state.
- SlotLoader, YAML manifests, third-party install, signing, and enterprise
  allowlist.
- Runtime permission enforcement and active health probes.
- SDK slot client and Web Slot Center.
- UI slot consumer.
- Persistence schema, ModelRouter/ProfileRegistry, external auth, worker
  behavior, or production deployment behavior changes.
- Production readiness declaration or external/operator gate closure.
