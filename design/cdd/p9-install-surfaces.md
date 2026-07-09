# P9 CDD: Slot Install Surfaces and Operator Controls

Status: Ready for Local Acceptance
Date: 2026-07-09

## 1. Overview

P9 exposes the existing local slot install workflow through HTTP, Python SDK,
TypeScript SDK, and the Web Slot Center while keeping install default-off and
server-side.

The work builds on ADR-0057 CLI install, ADR-0062 Ed25519 signatures, ADR-0065
package-aware v3 sidecars, and ADR-0060 bundle activation. YAML, marketplace,
remote URL install, upload install, and production plugin readiness remain out
of scope.

## 2. User Promise / JTBD

An operator can install a local slot from the daemon, SDK, or Web Slot Center
without learning the CLI command, while enterprise mode still applies allowlist,
signature, ACL, and audit controls.

A security reviewer can verify that install is still local-path, default-off,
server-side, auditable, rollback-safe, and not a marketplace or sandbox claim.

## 3. Scope

Included:

- `POST /v1/slots/install` accepting JSON `{source}`.
- Enterprise ACL for `resource_type=slot`, `permission=write`.
- Successful `slot_install` audit events through bootstrap install.
- Staged install writes with cleanup on copy failure.
- Python SDK sync/async slot list, get, and install methods.
- TypeScript SDK slot list, get, and install methods.
- Web Slot Center install modal gated by `VITE_DOGE_FEATURE_SLOT_INSTALL_UI`.
- SlotPolicy installed-slot allowance under active built-in bundles.
- Route count and SDK contract parity updates.

Excluded:

- URL install, upload install, marketplace/catalog behavior, remote registry, or
  trust-pipeline distribution.
- YAML manifests or YAML signing canonicalization.
- Client-side install policy, signature verification, or provider import.
- Default-on `slot_install`, default-on provider execution, or automatic bundle
  activation.
- Filesystem mediation, malicious-code containment, OS/container/WASM sandboxing,
  external gate closure, or production maturity.

## 4. Configuration

Backend install remains default off:

```text
DOGE_FEATURE_SLOT_PLATFORM=1
DOGE_FEATURE_SLOT_LOADER=1
DOGE_FEATURE_SLOT_INSTALL=0
```

Local install surface:

```text
DOGE_FEATURE_SLOT_INSTALL=1
DOGE_SLOT_INSTALL_DIR=<local install dir>
```

Enterprise install additionally requires:

```text
DOGE_AUTH_MODE=enterprise
DOGE_SLOT_ENTERPRISE_ALLOWLIST=<slot id>
DOGE_SLOT_TRUSTED_PUBLISHER_KEYS=<key_id=base64_ed25519_public_key>
enterprise_acl_grants: resource_type=slot, resource_id=<slot id>, permission=write
```

Web install UI remains separately default off:

```text
VITE_DOGE_FEATURE_SLOT_INSTALL_UI=0
```

## 5. Runtime Behavior

When `slot_install` is disabled, `POST /v1/slots/install` is unavailable and the
Web button remains hidden unless its frontend flag is explicitly enabled.

When enabled in local-demo mode, the route reads and validates the local manifest,
delegates to the same bootstrap install helper as CLI, emits audit metadata on
success, and refreshes slot/bundle snapshots in Web after install.

When enabled in enterprise mode, the route reads the manifest id before mutation,
requires the existing install allowlist/signature policy, and checks
`enterprise_acl_grants` for `resource_type=slot`, `resource_id=<slot id>`, and
`permission=write`.

Install writes stage files first. Copy failure removes the stage directory and
does not leave a final installed slot directory.

Active bundle filtering continues for built-in slots. Explicit slot ids installed
under `DOGE_SLOT_INSTALL_DIR` may resolve while a built-in bundle is active unless
they are disabled by policy.

## 6. Acceptance Criteria

- HTTP install is gated by `slot_install`.
- HTTP install reads manifest id before enterprise ACL and before mutation.
- Enterprise deny leaves no installed slot directory.
- Enterprise allow requires allowlist, verified signature, and `slot` write ACL.
- Successful install appends `slot_install` audit metadata.
- Installer rollback cleans partial staged state on copy failure.
- Python SDK and TypeScript SDK call server endpoints only.
- SDK contract parity includes slot list/get/install.
- Web install UI is hidden unless `VITE_DOGE_FEATURE_SLOT_INSTALL_UI` is enabled.
- Web install modal displays install result, `signature.status`, warnings, and
  install errors.
- Installed slots resolve under active built-in bundles without admitting
  unrelated built-in slots.
- Maturity posture remains:

```yaml
production_ready: false
stable_declaration: forbidden
level_3_sdk_platform: experimental
```

## 7. Verification Plan

Focused backend:

```text
py -3 -m pytest tests/unit/platform/slots/test_slot_install.py tests/unit/platform/slots/test_slot_policy.py tests/unit/platform/slots/test_slot_bundle.py tests/unit/platform/slots/test_builtin_gateway_slot.py tests/contract/test_slot_kernel_bundle_rows.py tests/contract/test_slot_api.py tests/contract/test_api_doc_route_coverage.py tests/unit/governance/test_s017_planning_docs.py -q
```

SDK:

```text
py -3 tools/ci/sdk-contract-check.py
npm test -- src\__tests__\client.spec.ts
```

Web:

```text
npm test -- src\stores\platform.spec.ts src\views\AdminCenterView.spec.ts
```

Governance:

```text
py -3 scripts/validate_alpha_maturity_honesty.py --file docs/progress/runtime-maturity.yaml
py -3 scripts/validate_plan_closure_gate.py --allow-open --source-plan C:\Users\WSMAN\.claude\plans\openclaw-rippling-sparkle.md
py -3 scripts/validate_docs_maturity_claims.py
py -3 scripts/validate_governance_yaml_shape.py
py -3 scripts/validate_adr_index_completeness.py
git diff --check
```
