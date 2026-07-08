# Sprint 047 CDD: Third-party Slot Install Preview

Status: Ready for Acceptance / Local Verification Passed
Date: 2026-07-07

Status Update - 2026-07-08: ADR-0062 upgrades the signature mechanism from
this sprint's v1 metadata sidecar to v2 Ed25519 cryptographic signatures,
trusted publisher keys, and SQLite key revocation. Sprint 047 remains the
manifest-only install-preview scope; provider entrypoints are still not
imported or executed, and `DOGE_FEATURE_SLOT_INSTALL` remains default off.

## 1. Overview

Sprint 047 adds a local third-party slot install preview.

The sprint introduces `SlotInstaller`, `SlotInstallPolicy`, sidecar signature
metadata validation, `DOGE_FEATURE_SLOT_INSTALL`, local install directory
settings, enterprise allowlist settings, and `doge slots install`.

The sprint does not import provider entrypoints, execute third-party Python,
add a marketplace, add HTTP install APIs, add SDK install methods, add YAML
parsing, or add OS sandboxing.

## 2. User Promise / JTBD

A local platform engineer can install a JSON slot manifest into a configured
local install directory and inspect it through the existing slot discovery
surfaces.

A security reviewer can verify that local install preview remains manifest-only
and that enterprise mode requires allowlist and trusted signature metadata.

## 3. Detailed Behavior

- `DOGE_FEATURE_SLOT_INSTALL` defaults to `false`.
- `DOGE_FEATURE_SLOT_PLATFORM=1` and `DOGE_FEATURE_SLOT_LOADER=1` are required.
- `DOGE_SLOT_INSTALL_DIR` controls where installed manifests are copied.
- `DOGE_SLOT_ENTERPRISE_ALLOWLIST` lists slot ids allowed in enterprise mode.
- `DOGE_SLOT_TRUSTED_SIGNERS` lists accepted sidecar metadata signers.
- `DOGE_SLOT_ALLOW_UNSIGNED_LOCAL` controls unsigned local-demo installs.
- `doge slots install <source>` accepts a JSON manifest file or a directory
  containing `slot.json`.
- Installation validates exactly one manifest.
- Installation copies the manifest to
  `<DOGE_SLOT_INSTALL_DIR>/<slot_id-with-underscores>/slot.json`.
- Optional `slot.signature.json` metadata is copied when present and valid.
- Installed manifests are loaded as manifest-only slots when the install flag is
  enabled.

## 4. Contracts / Data Model

Feature flags:

```text
DOGE_FEATURE_SLOT_PLATFORM=1
DOGE_FEATURE_SLOT_LOADER=1
DOGE_FEATURE_SLOT_INSTALL=1
```

Install settings:

```text
DOGE_SLOT_INSTALL_DIR=./data/slots
DOGE_SLOT_ENTERPRISE_ALLOWLIST=local.example
DOGE_SLOT_TRUSTED_SIGNERS=ops
DOGE_SLOT_ALLOW_UNSIGNED_LOCAL=1
```

Signature metadata:

```json
{
  "schema_version": 1,
  "slot_id": "local.example",
  "manifest_sha256": "...",
  "signer": "ops"
}
```

Maturity posture:

```yaml
production_ready: false
stable_declaration: forbidden
level_3_sdk_platform: experimental
```

## 5. Edge Cases

- Feature off: CLI returns disabled status.
- Source directory missing `slot.json`: install fails.
- Duplicate installed manifest with identical content: returns
  `already_installed`.
- Duplicate installed manifest with different content: install fails.
- Invalid sidecar JSON, slot id mismatch, or digest mismatch: install fails.
- Local unsigned manifest: allowed by default with warning.
- Enterprise unsigned or untrusted manifest: install fails.
- High-risk or shell-permission manifest: install fails by default.

## 6. Dependencies

- ADR-0042 Slot Platform Foundation.
- ADR-0055 Slot Permission and Health Enforcement.
- ADR-0056 Slot Loader and Bundle Activation.
- Existing CLI slot command group.

## 7. Configuration Knobs

- `DOGE_FEATURE_SLOT_INSTALL`: default `false`.
- `DOGE_SLOT_INSTALL_DIR`: default local data slot install directory.
- `DOGE_SLOT_ENTERPRISE_ALLOWLIST`: default empty.
- `DOGE_SLOT_TRUSTED_SIGNERS`: default empty.
- `DOGE_SLOT_ALLOW_UNSIGNED_LOCAL`: default `true`.

## 8. Acceptance Criteria

- `SlotInstaller`, `SlotInstallPolicy`, `SlotInstallResult`,
  `SlotSignatureVerification`, and `verify_slot_signature()` are exported from
  `doge.platform.slots`.
- `DOGE_FEATURE_SLOT_INSTALL` and install policy settings are documented and
  default safe.
- Capability discovery includes `feature.slot_install`.
- `doge slots install` is parser-covered and feature-gated.
- Local unsigned install copies the manifest and warns.
- Enterprise install requires allowlist + trusted signer + matching digest.
- Installed manifests join manifest-only discovery when install flag is on.
- No provider execution, HTTP route, SDK method, YAML parser, marketplace, or
  sandbox claim is added.

## 9. Validation Plan

```bash
py -3 -m pytest tests/unit/platform/slots/test_slot_install.py tests/test_settings.py tests/unit/use_cases/test_capability_registry.py tests/cli/test_cli_slots.py tests/contract/test_slot_kernel_bundle_rows.py -q
py -3 -m pytest tests/unit/platform/slots tests/contract/test_tool_registry_slot_parity.py tests/contract/test_agent_backends_slot_parity.py tests/contract/test_workflow_slot_parity.py tests/contract/test_governance_slot_parity.py tests/contract/test_watcher_slot_parity.py tests/contract/test_document_slot_parity.py tests/contract/test_data_source_slot_parity.py tests/contract/test_gateway_slot_parity.py tests/contract/test_eval_slot_parity.py tests/contract/test_slot_kernel_bundle_rows.py tests/contract/test_slot_ui_registry.py tests/contract/test_slot_api.py -q
py -3 tools/ci/sdk-contract-check.py
py -3 scripts/validate_import_boundaries.py
py -3 scripts/validate_docs_authority.py
py -3 scripts/validate_docs_links.py
py -3 scripts/validate_docs_maturity_claims.py
py -3 scripts/validate_alpha_maturity_honesty.py --file docs/architecture/adr-0057-third-party-slot-install-preview.md
py -3 scripts/validate_alpha_maturity_honesty.py --file design/cdd/sprint-047-third-party-slot-install-preview.md
py -3 scripts/validate_adr_index_completeness.py
py -3 scripts/validate_governance_yaml_shape.py
py -3 scripts/validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/openclaw-like-magical-barto.md
git diff --check
cmd.exe /c git diff --check
```

## 10. Local Verification Result

Local verification passed:

- Focused install/settings/capability/CLI/kernel suite: 65 tests.
- Broad slot parity suite: 173 tests, with 2 known FastAPI deprecation warnings.
- SDK contract: 15 surfaces and 15 entity parity checks.
- Import boundaries, docs authority, docs links, docs maturity claims,
  ADR/CDD maturity honesty, ADR index, governance YAML, acceptable-open plan
  closure, and WSL/Windows whitespace checks passed.
- Plan closure remains intentionally open for external/operator-owned gates:
  2 passed, 4 open, 0 failed, 0 invalid.

## 11. Out of Scope

- Provider entrypoint import or arbitrary Python plugin execution.
- Marketplace or registry download flow.
- Cryptographic signature format in Sprint 047; ADR-0062 later adds v2
  Ed25519 manifest signatures without changing the manifest-only install
  boundary.
- HTTP install API.
- SDK slot client methods.
- YAML manifest parsing.
- OS sandboxing, subprocess isolation, network interception, filesystem
  mediation, or database/secret access interception.
- Production readiness declaration or external/operator gate closure.
