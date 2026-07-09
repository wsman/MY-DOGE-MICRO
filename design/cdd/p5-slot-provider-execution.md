# P5 CDD: Slot Provider Execution

Status: Ready for Acceptance / Local Verification In Progress
Date: 2026-07-08

## 1. Overview

P5 adds a default-off local alpha execution path for installed, trusted slot
providers. It narrows the historical "manifest-only forever" posture without
changing the default discovery behavior: `SlotLoader` still loads JSON
manifests as `ManifestOnlySlot`, while bootstrap may replace an installed
manifest with `InstalledProviderSlot` only when all execution gates pass.

P5 does not add OS/container/WASM sandboxing, filesystem mediation,
malicious-code containment, provider package signing, marketplace behavior,
HTTP install APIs, SDK install APIs, YAML manifests, external gate closure, or
production-readiness changes.

## 2. User Promise / JTBD

A platform engineer can install a signed local slot manifest and see exactly
why it is or is not execution eligible.

A plugin author can prove an `ISlot` provider path for workflow, tool, model,
data, or document facets under a controlled local alpha gate.

A security reviewer can verify that provider execution remains default off,
requires signing/revocation/runtime interception, and is not represented as an
OS sandbox or production plugin ecosystem.

## 3. Execution Gates

Provider import and resolve are allowed only when all of these are true:

1. `slot_platform`, `slot_loader`, and `slot_install` are enabled.
2. The manifest is installed under `DOGE_SLOT_INSTALL_DIR`.
3. The installed manifest signature reverifies as `verified`.
4. Trusted publisher keys are configured.
5. Signing-key revocation was checked and the key is not revoked.
6. Enterprise mode also has the slot id in `DOGE_SLOT_ENTERPRISE_ALLOWLIST`.
7. `slot_runtime_interception` is enabled.
8. `slot_provider_execution` is enabled.
9. SlotKernel policy/enforcement admits the slot before `resolve()`.

## 4. Detailed Behavior

- `DOGE_FEATURE_SLOT_PROVIDER_EXECUTION` defaults to `false`.
- Capability discovery exposes `feature.slot_provider_execution` as high risk.
- `build_slot_status_rows()` reports `execution_eligible`,
  `execution_blockers`, and nested `execution` metadata.
- Status discovery does not import provider modules.
- Manifest dirs configured by `DOGE_SLOT_MANIFEST_DIRS` remain non-installed
  manifest-only slots.
- Installed slots that fail any gate remain manifest-only for discovery.
- Installed slots that pass all non-admission gates register as
  `InstalledProviderSlot`.
- `InstalledProviderSlot.resolve()` repeats signature/revocation verification
  before importlib entrypoint execution.
- Provider entrypoints must instantiate `doge.platform.slots.ISlot`.
- Provider manifest `id`, `type`, and `provides` must match the installed
  manifest.
- Restricted contribution facets are rejected after resolve.

## 5. Allowed Facets

Allowed installed-provider facets:

- `tools`
- `model_backends`
- `workflows`
- `data_sources`
- `document_parsers`

Restricted installed-provider facets:

- `routes`
- `ui_panels`
- `watchers`
- `eval_suites`
- `governance_policies`

Status update - 2026-07-09: ADR-0068/P10 moves only `eval_suites` out of this
restricted list for installed, v3 package-signed, operator-gated providers.
`routes`, `ui_panels`, `watchers`, and `governance_policies` remain restricted.

Status update - 2026-07-09: ADR-0069/P10 also moves static `ui_panels` metadata
out of this restricted list for installed, v3 package-signed, operator-gated
providers. `routes`, `watchers`, and `governance_policies` remain restricted.

## 6. Configuration

```text
DOGE_FEATURE_SLOT_PROVIDER_EXECUTION=1
```

Required companion gates:

```text
DOGE_FEATURE_SLOT_PLATFORM=1
DOGE_FEATURE_SLOT_LOADER=1
DOGE_FEATURE_SLOT_INSTALL=1
DOGE_FEATURE_SLOT_RUNTIME_INTERCEPTION=1
DOGE_SLOT_TRUSTED_PUBLISHER_KEYS=<key_id=base64_ed25519_public_key>
```

Enterprise deployments must also configure:

```text
DOGE_AUTH_MODE=enterprise
DOGE_SLOT_ENTERPRISE_ALLOWLIST=<slot_id>
```

## 7. Acceptance Criteria

- Default settings keep provider execution disabled.
- CLI/API status rows include execution eligibility and blockers.
- Status rows do not import provider code.
- Missing signatures block execution.
- Revoked signing keys block execution.
- Enterprise allowlist omissions block execution.
- Runtime interception disabled blocks execution.
- All gates passing allows provider import and contribution resolution.
- Restricted facets fail closed.
- `doge.platform.slots` remains a pure contract package.
- Maturity posture remains:

```yaml
production_ready: false
stable_declaration: forbidden
level_3_sdk_platform: experimental
```

## 8. Verification Plan

Focused backend:

```bash
py -3 -m pytest tests/unit/platform/slots/test_slot_provider_execution.py tests/test_settings.py tests/unit/use_cases/test_capability_registry.py tests/cli/test_cli_slots.py tests/contract/test_slot_api.py -q
```

Boundary and slot regression:

```bash
py -3 -m pytest tests/unit/architecture/test_slot_boundary.py tests/unit/platform/slots/test_slot_install.py tests/unit/platform/slots/test_slot_runtime_access.py tests/contract/test_tool_registry_slot_parity.py tests/contract/test_data_source_slot_parity.py -q
```

Governance:

```bash
py -3 scripts/validate_adr_index_completeness.py
py -3 scripts/validate_governance_yaml_shape.py
py -3 scripts/validate_docs_authority.py
py -3 scripts/validate_docs_maturity_claims.py
```
