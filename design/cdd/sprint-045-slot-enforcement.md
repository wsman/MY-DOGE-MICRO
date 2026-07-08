# Sprint 045 CDD: Slot Permission and Health Enforcement

Status: Ready for Acceptance / Local Verification Passed
Date: 2026-07-07

## 1. Overview

Sprint 045 adds the first runtime enforcement seam for Slot Platform
permissions and health.

The sprint introduces `SlotEnforcementPolicy`, wires it into `SlotKernel`, adds
`DOGE_FEATURE_SLOT_ENFORCEMENT`, exposes capability metadata, and prevents
enforcement-blocked tool slots from reappearing through legacy fallback tool
registration.

The sprint does not add OS sandboxing, network interception, filesystem
mediation, third-party slot install, signing, enterprise allowlists, bundle
activation, external gate closure, or production-readiness changes.

Later status: P4 / ADR-0063 adds a separate default-off in-process runtime
interception layer for guarded db/secret/network ports and subprocess env/cwd
hardening. Sprint 045's scope and ADR-0055 still describe only SlotKernel
resolution-time admission enforcement; OS/container/WASM sandboxing,
filesystem mediation, provider execution, and production readiness remain out
of scope.

## 2. User Promise / JTBD

A platform engineer can enable slot enforcement locally and see manifest
permissions/health affect slot status and contribution resolution.

A security reviewer can verify that shell-permission and disabled-health slots
are blocked before their contributions reach runtime consumers.

A future SlotLoader/install sprint has a concrete guard to use before loading
untrusted or operator-provided slot manifests.

## 3. Detailed Behavior

- `DOGE_FEATURE_SLOT_ENFORCEMENT` defaults to `false`.
- `FeatureConfig.slot_enforcement` reads `DOGE_FEATURE_SLOT_ENFORCEMENT`.
- Capability discovery exposes `feature.slot_enforcement`.
- `SlotEnforcementPolicy` is inert by default.
- When enabled through bootstrap:
  - permission checks reject `risk_level=forbidden`;
  - permission checks reject `shell=allow` unless policy explicitly allows it;
  - active health probes call `ISlot.health(context)`;
  - disabled health blocks status resolution and contribution resolve/start;
  - degraded health is reported but allowed by default.
- `SlotKernel.status()` reports active health status when enforcement is on.
- `SlotKernel.bundle_status()` uses the same enforcement decision as slot
  status.
- `SlotKernel.resolve_contributions()` and `SlotKernel.start()` skip blocked
  slots.
- `build_slot_aware_tool_registry()` reserves tool names declared by tool slot
  manifests before resolving contributions, so blocked tool slots do not fall
  back to legacy registration.

## 4. Contracts / Data Model

Enforcement policy:

```python
SlotEnforcementPolicy(
    enforce_permissions=True,
    enforce_health=True,
)
```

Decision:

```python
SlotEnforcementDecision(
    allowed=False,
    reason="slot tool.shell declares shell permission",
)
```

Feature flag:

```text
DOGE_FEATURE_SLOT_PLATFORM=1
DOGE_FEATURE_SLOT_ENFORCEMENT=1
```

Maturity posture:

```yaml
production_ready: false
stable_declaration: forbidden
level_3_sdk_platform: experimental
```

## 5. Edge Cases

- Enforcement off: existing slot-aware behavior remains unchanged.
- Shell permission declared: slot is disabled/skipped unless policy allows
  shell.
- Forbidden risk declared: slot is disabled/skipped unless policy allows
  forbidden risk.
- Disabled health: slot is disabled/skipped.
- Degraded health: slot is reported degraded but still resolves by default.
- Health probe exception: status reports degraded health instead of raising.
- Blocked tool slot: declared tool names are not re-registered from the legacy
  fallback registry.

## 6. Dependencies

- ADR-0042 Slot Platform Foundation.
- ADR-0052 Slot Kernel, Bundles, Policy, and Lifecycle.
- ADR-0054 Web Slot Center.
- Existing ToolRegistry and slot-aware tool registry factory.

## 7. Configuration Knobs

- `DOGE_FEATURE_SLOT_PLATFORM`: default `false`; gates slot contribution
  resolution.
- `DOGE_FEATURE_SLOT_ENFORCEMENT`: default `false`; enables runtime permission
  and health enforcement inside SlotKernel.

No enterprise allowlist, SlotLoader flag, sandbox flag, or bundle activation
flag is added in this sprint.

## 8. Acceptance Criteria

- `SlotEnforcementPolicy` and `SlotEnforcementDecision` are exported from
  `doge.platform.slots`.
- `SlotKernel` applies enforcement in status, bundle status, resolve, and
  start.
- `SlotKernel` calls active health probes when enforcement is enabled.
- Disabled-health slots are disabled/skipped.
- Degraded-health slots are reported and allowed by default.
- Shell-permission slots are blocked by default under enforcement.
- `DOGE_FEATURE_SLOT_ENFORCEMENT` is documented and default-off.
- Capability discovery includes `feature.slot_enforcement`.
- A blocked tool slot cannot fall back to legacy tool registration.
- No backend route count, SDK public surface, SlotLoader, bundle activation,
  third-party install/signing, production readiness declaration, or
  external/operator gate closure is added.

## 9. Validation Plan

```bash
py -3 -m pytest tests/test_settings.py tests/unit/use_cases/test_capability_registry.py tests/unit/platform/slots/test_slot_enforcement.py tests/unit/platform/slots/test_slot_kernel.py tests/contract/test_tool_registry_slot_parity.py tests/cli/test_cli_slots.py tests/cli/test_doged_cli.py -q
py -3 -m pytest tests/unit/platform/slots tests/contract/test_tool_registry_slot_parity.py tests/contract/test_agent_backends_slot_parity.py tests/contract/test_workflow_slot_parity.py tests/contract/test_governance_slot_parity.py tests/contract/test_watcher_slot_parity.py tests/contract/test_document_slot_parity.py tests/contract/test_data_source_slot_parity.py tests/contract/test_gateway_slot_parity.py tests/contract/test_eval_slot_parity.py tests/contract/test_slot_kernel_bundle_rows.py tests/contract/test_slot_ui_registry.py tests/contract/test_slot_api.py -q
py -3 tools/ci/sdk-contract-check.py
py -3 scripts/validate_import_boundaries.py
py -3 scripts/validate_docs_authority.py
py -3 scripts/validate_docs_links.py
py -3 scripts/validate_docs_maturity_claims.py
py -3 scripts/validate_alpha_maturity_honesty.py --file docs/architecture/adr-0055-slot-enforcement.md
py -3 scripts/validate_alpha_maturity_honesty.py --file design/cdd/sprint-045-slot-enforcement.md
py -3 scripts/validate_adr_index_completeness.py
py -3 scripts/validate_governance_yaml_shape.py
py -3 scripts/validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/openclaw-like-magical-barto.md
git diff --check
cmd.exe /c git diff --check
```

## 10. Local Verification Result

Local verification passed and is recorded in
`production/qa/evidence/sprint-045-slot-enforcement-manifest.md`.

- Focused settings/capability/enforcement/kernel/tool/CLI suite: 84 tests.
- Broad slot parity suite: 156 tests.
- SDK contract: 15 surfaces / 15 entity parity checks.
- Import boundaries, docs authority, docs links, docs maturity claims,
  ADR/CDD maturity honesty, ADR index, governance YAML, acceptable-open plan
  closure, and WSL/Windows whitespace checks passed.
- Closure posture remains intentionally open for operator-owned external gates:
  2 passed, 4 open, 0 failed, 0 invalid.

## 11. Out of Scope

- OS sandboxing or subprocess isolation.
- Network, filesystem, database, or secret access interception.
- SlotLoader and disk manifests.
- Bundle activation and persistent enable/disable state.
- Third-party slot install, signing, and enterprise allowlist.
- SDK slot client methods.
- Production readiness declaration or external/operator gate closure.

P4 / ADR-0063 later releases only the db/secret/network guarded-port
interception and subprocess env/cwd hardening subset. The remaining out-of-scope
items above still apply to Sprint 045 history and to production readiness.
