# Sprint 046 CDD: Slot Loader and Bundle Activation

Status: Ready for Acceptance / Local Verification Passed
Date: 2026-07-07

## 1. Overview

Sprint 046 adds the first local SlotLoader and bundle activation slice.

The sprint introduces a JSON-only `SlotLoader`, manifest-only disk slots,
`DOGE_FEATURE_SLOT_LOADER`, `DOGE_SLOT_MANIFEST_DIRS`, process-local bundle
activation, CLI bundle list/activate commands, and
`POST /v1/slot-bundles/{bundle_id}/activate`.

The sprint does not add YAML parsing, provider entrypoint imports,
third-party slot install, signing, enterprise allowlists, persistent activation
state, SDK slot client methods, OS sandboxing, or production-readiness changes.

## 2. User Promise / JTBD

A platform engineer can point MY-DOGE at local JSON slot manifests and verify
that the manifests are valid, discoverable, and governed without executing
provider code.

A local operator can activate a built-in bundle for the current process and see
runtime contribution resolution constrained by that bundle.

A reviewer can distinguish local manifest preview and process-local activation
from a real third-party plugin ecosystem.

## 3. Detailed Behavior

- `DOGE_FEATURE_SLOT_LOADER` defaults to `false`.
- `DOGE_SLOT_MANIFEST_DIRS` is a CSV list of JSON manifest files or manifest
  directories.
- `SlotLoader` discovers direct `*.json` files and nested `*/slot.json` files.
- Loaded disk manifests become `ManifestOnlySlot` instances.
- `ManifestOnlySlot.resolve()` returns an empty `SlotContribution`; it does not
  import provider code or execute slot entrypoints.
- `build_builtin_slot_registry()` registers manifest-only slots only when the
  loader flag and manifest dirs are configured.
- `SlotBundleActivationState` stores a single active bundle id in memory.
- `policy_for_activation()` converts active bundle state into `SlotPolicy`.
- `build_builtin_slot_kernel()` applies active bundle policy when the loader
  flag is on and no explicit policy is supplied.
- `build_slot_bundle_rows()` includes an `active` boolean.
- `doge slots bundle list` prints built-in bundle status.
- `doge slots bundle activate <bundle_id>` requires
  `DOGE_FEATURE_SLOT_LOADER=1`.
- `POST /v1/slot-bundles/{bundle_id}/activate` requires
  `DOGE_FEATURE_SLOT_PLATFORM=1` and `DOGE_FEATURE_SLOT_LOADER=1`.
- HTTP route authority now tracks 96 product routes.

## 4. Contracts / Data Model

Feature flags:

```text
DOGE_FEATURE_SLOT_PLATFORM=1
DOGE_FEATURE_SLOT_LOADER=1
```

Manifest dirs:

```text
DOGE_SLOT_MANIFEST_DIRS=/path/to/slot.json,/path/to/slots
```

Activation response:

```json
{
  "status": "activated",
  "active_bundle_id": "bundle.daemon_operator",
  "bundle": {
    "id": "bundle.daemon_operator",
    "active": true
  }
}
```

Maturity posture:

```yaml
production_ready: false
stable_declaration: forbidden
level_3_sdk_platform: experimental
```

## 5. Edge Cases

- Loader off: disk manifests are ignored and activation APIs are disabled.
- Slot platform off: activation fails closed because slot APIs are unavailable.
- Missing manifest source: loader raises `SlotConfigurationError`.
- Invalid manifest JSON/schema: loader raises `SlotConfigurationError` with the
  manifest path.
- Duplicate manifest file path discovered through multiple patterns: loaded
  once.
- Unknown active bundle id: policy resolution fails fast.
- Manifest-only slot: visible in discovery but contributes no runtime behavior.
- Active bundle: filters enabled and disabled slot ids for the current process
  only.

## 6. Dependencies

- ADR-0042 Slot Platform Foundation.
- ADR-0052 Slot Kernel, Bundles, Policy, and Lifecycle.
- ADR-0055 Slot Permission and Health Enforcement.
- Existing CLI, FastAPI slot router, and bootstrap slot factories.

## 7. Configuration Knobs

- `DOGE_FEATURE_SLOT_PLATFORM`: default `false`; gates slot discovery.
- `DOGE_FEATURE_SLOT_LOADER`: default `false`; gates disk manifest loading and
  bundle activation.
- `DOGE_SLOT_MANIFEST_DIRS`: default empty; CSV list of manifest files or dirs.

No YAML dependency, third-party install flag, signing flag, enterprise allowlist
flag, SDK flag, sandbox flag, or persistence flag is added in this sprint.

## 8. Acceptance Criteria

- `SlotLoader`, `ManifestOnlySlot`, `SlotBundleActivationState`, and
  `policy_for_activation()` are exported from `doge.platform.slots`.
- `DOGE_FEATURE_SLOT_LOADER` and `DOGE_SLOT_MANIFEST_DIRS` are documented and
  default off/empty.
- Capability discovery includes `feature.slot_loader`.
- JSON manifests can be loaded from files and directories.
- Manifest-only disk slots appear in slot status rows when the loader is
  enabled.
- Active bundle policy constrains `SlotKernel` resolution.
- CLI supports `doge slots bundle list` and `doge slots bundle activate`.
- API supports feature-gated
  `POST /v1/slot-bundles/{bundle_id}/activate`.
- Route docs and governance registries agree on 96 HTTP routes.
- No provider entrypoint import, YAML parsing, third-party install/signing,
  enterprise allowlist, persistent activation, SDK slot client, sandboxing,
  production readiness declaration, or external/operator gate closure is added.

## 9. Validation Plan

```bash
py -3 -m pytest tests/test_settings.py tests/unit/use_cases/test_capability_registry.py tests/unit/platform/slots/test_slot_loader.py tests/unit/platform/slots/test_slot_activation.py tests/contract/test_slot_kernel_bundle_rows.py tests/contract/test_slot_api.py tests/cli/test_cli_slots.py tests/cli/test_doged_cli.py -q
py -3 -m pytest tests/unit/platform/slots tests/contract/test_tool_registry_slot_parity.py tests/contract/test_agent_backends_slot_parity.py tests/contract/test_workflow_slot_parity.py tests/contract/test_governance_slot_parity.py tests/contract/test_watcher_slot_parity.py tests/contract/test_document_slot_parity.py tests/contract/test_data_source_slot_parity.py tests/contract/test_gateway_slot_parity.py tests/contract/test_eval_slot_parity.py tests/contract/test_slot_kernel_bundle_rows.py tests/contract/test_slot_ui_registry.py tests/contract/test_slot_api.py -q
py -3 -m pytest tests/contract/test_api_doc_route_coverage.py tests/unit/governance/test_s017_planning_docs.py -q
py -3 tools/ci/sdk-contract-check.py
py -3 scripts/validate_import_boundaries.py
py -3 scripts/validate_docs_authority.py
py -3 scripts/validate_docs_links.py
py -3 scripts/validate_docs_maturity_claims.py
py -3 scripts/validate_alpha_maturity_honesty.py --file docs/architecture/adr-0056-slot-loader-bundle-activation.md
py -3 scripts/validate_alpha_maturity_honesty.py --file design/cdd/sprint-046-slot-loader-bundle-activation.md
py -3 scripts/validate_adr_index_completeness.py
py -3 scripts/validate_governance_yaml_shape.py
py -3 scripts/validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/openclaw-like-magical-barto.md
git diff --check
cmd.exe /c git diff --check
```

## 10. Local Verification Result

Local verification passed and is recorded in
`production/qa/evidence/sprint-046-slot-loader-bundle-activation-manifest.md`.

- Focused settings/capability/loader/activation/API/CLI/route-governance suite:
  138 tests.
- Broad slot parity suite: 167 tests.
- SDK contract: 15 surfaces / 15 entity parity checks.
- Import boundaries, docs authority, docs links, docs maturity claims,
  ADR/CDD maturity honesty, ADR index, governance YAML, acceptable-open plan
  closure, and WSL/Windows whitespace checks passed.
- Closure posture remains intentionally open for operator-owned external gates:
  2 passed, 4 open, 0 failed, 0 invalid.

## 11. Out of Scope

- YAML manifest parsing.
- Provider entrypoint import or arbitrary Python plugin execution.
- Third-party slot install workflow.
- Signature verification and enterprise allowlists.
- Persistent bundle activation or cross-process synchronization.
- SDK slot client methods.
- OS sandboxing, subprocess isolation, network interception, filesystem
  mediation, or database/secret access interception.
- Production readiness declaration or external/operator gate closure.
