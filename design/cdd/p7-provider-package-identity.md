# P7 CDD: Provider Package Identity

Status: Ready for Acceptance / Local Verification Passed
Date: 2026-07-08

## 1. Overview

P7 closes the Slot Platform manifest-only signing gap for installed provider
execution. It introduces a deterministic package digest, v3 package-aware
`slot.signature.json` sidecars, package copy semantics, resolve-time package
reverification, path-confined provider imports, and minimal successor-key
metadata.

P7 does not add malicious-code containment, filesystem mediation,
OS/container/WASM isolation, transitive dependency signing, marketplace
behavior, HTTP install APIs, SDK install APIs, external gate closure, remote CI
promotion, or maturity promotion.

## 2. User Promise / JTBD

A platform engineer can sign a local provider package and prove that the
installed package bytes match what the trusted publisher signed.

A plugin author can keep using a simple local directory layout while moving
from v2 manifest-only signatures to v3 package-aware signatures.

A security reviewer can verify that v2 sidecars remain manifest-only and that
provider execution requires package identity, resolve-time recheck, revocation
lookup, runtime interception, and SlotKernel admission.

## 3. Package Layout

Package-aware installed slots use:

```text
<DOGE_SLOT_INSTALL_DIR>/<slot_dir_name>/
  slot.json
  slot.signature.json
  package/
    <python_package>/
      __init__.py
      provider.py
      helper.py
```

The manifest `entrypoint` must point to a dotted object inside `package/`, for
example:

```text
vendor_package.provider.ProviderSlot
```

There is no pip, wheel, marketplace, or remote package registry in P7.

## 4. Digest And Binding

`package_tree_digest(package_dir)` computes `sha256_tree_v1`:

- walk every file under `package/`;
- reject symlinks, non-files, path escapes, non-directory package roots, and
  empty packages;
- hash file bytes with chunked SHA-256 reads;
- normalize relative paths with POSIX separators;
- sort entries lexicographically by relative path;
- canonical-JSON encode the sorted file list;
- hash that canonical list to produce the package digest value.

v3 `slot.signature.json` binds:

- canonical manifest bytes;
- canonical package digest bytes;
- Ed25519 signature;
- trusted `key_id`;
- `manifest_sha256`;
- `package_digest`.

v2 sidecars keep their existing manifest-only behavior. They remain valid for
install/discovery compatibility, but provider execution must reject them because
they do not include `package_digest`.

## 5. Trust Model

Provider execution is allowed only when all P5 gates still pass plus the P7
package identity gate:

1. `slot_platform`, `slot_loader`, `slot_install`,
   `slot_runtime_interception`, and `slot_provider_execution` are enabled.
2. The slot is installed under `DOGE_SLOT_INSTALL_DIR`.
3. The installed sidecar verifies as v3 package-aware.
4. Trusted publisher keys are configured.
5. Signing-key revocation lookup succeeds and the key is not revoked.
6. Enterprise mode also has the slot id in `DOGE_SLOT_ENTERPRISE_ALLOWLIST`.
7. SlotKernel policy/enforcement admits the slot before `resolve()`.

`SlotLoader` and `DOGE_SLOT_MANIFEST_DIRS` remain manifest-only and must not
import provider code.

## 6. Import Behavior

Provider import must load from:

```text
<installed slot dir>/package/
```

The loader uses `importlib.util.spec_from_file_location()` and
`submodule_search_locations` for package helper modules. It rejects module paths
that escape the resolved package root and does not use arbitrary `sys.path`
lookup for the entrypoint module when the signed package exists.

The loader disables bytecode writes during provider import so import-time
`__pycache__` files do not mutate the signed package tree.

Transitive imports outside the signed provider package remain normal Python
imports. P7 signs the provider package, not its full dependency tree.

## 7. Rotation Metadata

Signing keys remain versionable by convention, for example:

```text
ops@v1
ops@v2
```

`slot_signer_revocations` gains nullable `successor_key_id`. The CLI exposes
this with:

```text
doge slots revoke-key ops@v1 --successor-key-id ops@v2
```

The successor field is operator metadata only. It does not automatically trust
the successor key, create validity windows, or define grace periods.

## 8. Configuration And CLI

New CLI behavior:

```text
doge slots sign <slot.json> --key <private-key.pem> --package-dir <package>
```

This writes a v3 sidecar with `package_digest`.

Existing behavior remains:

```text
doge slots sign <slot.json> --key <private-key.pem>
```

This writes a v2 manifest-only sidecar.

Existing feature defaults stay conservative:

```yaml
slot_install: false
slot_runtime_interception: false
slot_provider_execution: false
production_ready: false
stable_declaration: forbidden
level_3_sdk_platform: experimental
```

## 9. Acceptance Criteria

- `package_tree_digest()` is deterministic and stdlib-only.
- v3 sidecars sign canonical manifest bytes plus canonical package digest
  bytes.
- v3 verification recomputes the package tree and fails closed on missing,
  malformed, mismatched, or unsupported package digest data.
- `doge slots sign --package-dir` writes v3 sidecars; without `--package-dir`
  it still writes v2 sidecars.
- `SlotInstaller` copies `package/` only for package-aware v3 installs and
  preserves v1/v2 manifest-only install behavior.
- Provider execution rejects v2 manifest-only signatures.
- Provider execution repeats package-aware verification at resolve time.
- Provider import loads from the installed signed package, not a typosquatted
  module on `sys.path`.
- Revocation records can store and display `successor_key_id`.
- P7 remains a local alpha identity hardening step, not runtime containment.

## 10. Validation Plan

```bash
py -3 -m pytest tests\unit\platform\slots\test_slot_install.py tests\unit\platform\slots\test_slot_provider_execution.py tests\unit\infrastructure\test_slot_signing_repository.py tests\cli\test_cli_slots.py -q
py -3 -m pytest tests\unit\architecture\test_slot_boundary.py tests\contract\test_slot_api.py tests\contract\test_slot_kernel_bundle_rows.py -q
py -3 scripts\validate_import_boundaries.py
py -3 scripts\validate_alpha_maturity_honesty.py --file docs\progress\runtime-maturity.yaml
py -3 scripts\validate_alpha_maturity_honesty.py --file docs\architecture\adr-0065-provider-package-identity.md
py -3 scripts\validate_alpha_maturity_honesty.py --file design\cdd\p7-provider-package-identity.md
py -3 scripts\validate_alpha_maturity_honesty.py --file C:\Users\WSMAN\.claude\plans\openclaw-rippling-sparkle.md
py -3 scripts\validate_plan_closure_gate.py --allow-open --source-plan C:\Users\WSMAN\.claude\plans\openclaw-rippling-sparkle.md
py -3 scripts\validate_docs_links.py
py -3 scripts\validate_docs_maturity_claims.py
py -3 scripts\validate_governance_yaml_shape.py
py -3 scripts\validate_adr_index_completeness.py
git diff --check
```

## 11. Local Verification Result

Local verification passed and is recorded in
`production/qa/evidence/slot-provider-package-identity-local-acceptance-2026-07-08.md`.

- Focused provider package/signing/repository/CLI suite: 57 tests.
- Migration suite: 7 tests.
- Architecture/API slot regression: 44 tests with 2 known FastAPI deprecation
  warnings.
- Docs consistency: 7 tests.
- Import boundaries, alpha maturity honesty, plan closure, docs links, docs
  maturity claims, governance YAML, ADR index, and Windows/WSL whitespace checks
  passed.
- Closure posture remains intentionally open for operator-owned external gates:
  2 passed, 4 open, 0 failed, 0 invalid.

## 12. Out Of Scope

- Full runtime isolation.
- Filesystem mediation.
- Raw network denial.
- Raw sqlite, subprocess, or direct OS API containment.
- Transitive dependency signing.
- Sigstore/cosign.
- HTTP install API, SDK install API, Web install flow, marketplace, YAML
  manifest parser.
- Remote CI assertion, latest remotely verified SHA promotion, external gate
  closure, or maturity promotion.
