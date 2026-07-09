# ADR-0065: Provider Package Identity

## Status

Accepted

## Date

2026-07-08

## Decision Makers

wsman (product owner) / implementation agent

## Summary

P7 extends slot signing from manifest-only identity to manifest plus provider
package identity for local installed provider execution.

The decision adds v3 `slot.signature.json` sidecars. A v3 sidecar uses the same
trusted Ed25519 publisher key model as ADR-0062, but signs:

```text
canonical_manifest_bytes + canonical_package_digest_bytes
```

The package digest is a deterministic `sha256_tree_v1` hash over the installed
provider `package/` directory. Provider execution now requires a verified v3
package-aware signature. v2 sidecars still verify for manifest-only install and
discovery compatibility, but they do not unlock provider execution.

P7 also replaces arbitrary `sys.path` entrypoint imports with a path-confined
import from the installed signed `package/` directory and adds minimal signing
key successor metadata for local rotation records.

This ADR closes the P5 gap where a signed manifest could point at tampered or
swapped package code. It does not add malicious-code containment, filesystem
mediation, OS/container/WASM isolation, transitive dependency signing, HTTP
install APIs, SDK install APIs, marketplace behavior, external gate closure,
remote CI promotion, or maturity promotion.

Status Update - 2026-07-09: ADR-0066 uses ADR-0065's package identity as
context, but it does not turn package identity into provider runtime
containment. ADR-0066 adds default-off Windows Job Object resource limits only
for `run_python_analysis` code strings; installed provider contribution objects
remain in-process and `provider_contribution_isolation=not_provided`.

Status Update - 2026-07-09: ADR-0067 adds default-off HTTP, SDK, and Web install
surfaces that preserve ADR-0065 package-aware v3 sidecar semantics. P9 install
may copy verified packages through the existing installer, but it does not add
transitive dependency signing, filesystem mediation, marketplace behavior, YAML
manifests, or provider runtime containment.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python 3.10+; stdlib `hashlib`/`json`/`importlib.util`; `cryptography==44.0.2`; SQLite; existing Slot Platform contracts |
| **Domain** | Security / CLI / Slot Platform local alpha provider execution |
| **Knowledge Risk** | MEDIUM - package identity and import confinement rely on Python importlib and local filesystem behavior |
| **References Consulted** | `docs/reference/python/VERSION.md`, `standards/technical-preferences.md`, `docs/registry/architecture.yaml`, `docs/architecture/adr-0062-slot-cryptographic-signing.md`, `docs/architecture/adr-0064-slot-provider-execution.md`, `C:\Users\WSMAN\.claude\plans\openclaw-rippling-sparkle.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | v3 signature/package tamper tests, v2 manifest-only execution blocker tests, import path confinement tests, successor metadata tests, CLI sign tests, slot boundary tests, docs/governance validators, alpha maturity honesty, acceptable-open plan closure, whitespace checks |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0062 (Slot Cryptographic Signing), ADR-0064 (Slot Provider Execution) |
| **Extends** | ADR-0062 by adding v3 package-aware Ed25519 sidecars; ADR-0064 by requiring package-aware signatures and path-confined imports before provider execution |
| **Supersedes** | ADR-0062's P3 limitation that signatures cover only manifests, and ADR-0064's P5 limitation that provider package code is not signed, only for local installed package identity |
| **Enables** | ADR-0066 code-string boundary documentation and later provider-runner/container/WASM isolation work with a trustworthy local package identity input |
| **Blocks** | Any claim that v2 manifest-only signatures unlock provider execution, or that P7 provides OS/container/WASM isolation, malicious-code containment, marketplace install, transitive dependency signing, external gate closure, or maturity promotion |
| **Ordering Note** | P7 landed before ADR-0066 so later isolation work can reason about which local package bytes are being executed. ADR-0066 covers code strings only; provider runtime containment still requires a separate runner/container/WASM decision. |

## Context

ADR-0062 added Ed25519 manifest signatures. ADR-0064 used those verified
signatures as one gate for installed-provider execution. That was enough to
prove a local execution seam, but not enough to bind the executed Python bytes
to the trusted publisher identity.

Before P7, a valid signed manifest could name an entrypoint that resolved to a
different module on `sys.path`, and install copied no package code. A local
operator could therefore execute tampered or swapped code while the manifest
signature still verified.

P7 narrows that gap without jumping to a package manager, wheel format,
Sigstore, or sandbox. The local alpha unit of identity is a directory named
`package/` beside the installed `slot.json`.

## Constraints

- Keep `DOGE_FEATURE_SLOT_INSTALL`, `DOGE_FEATURE_SLOT_RUNTIME_INTERCEPTION`,
  and `DOGE_FEATURE_SLOT_PROVIDER_EXECUTION` default `false`.
- Keep v1 legacy and v2 manifest-only sidecar compatibility.
- Require v3 package-aware signatures for provider execution.
- Keep `SlotLoader` and `DOGE_SLOT_MANIFEST_DIRS` manifest-only.
- Keep package signing local-first and Ed25519-only.
- Do not add a pip/wheel install surface, HTTP install API, SDK install API,
  YAML parser, marketplace, Sigstore/cosign verification, validity windows, or
  grace periods in P7.
- Preserve `production_ready: false`, `stable_declaration: forbidden`, and
  `level_3_sdk_platform: experimental`.

## Decision

### Package Layout

Installed package-aware slots use:

```text
<DOGE_SLOT_INSTALL_DIR>/<slot_dir_name>/
  slot.json
  slot.signature.json
  package/
    <python_package>/
      __init__.py
      provider.py
      ...
```

The manifest `entrypoint` points at a dotted object inside `package/`, for
example:

```text
vendor_example.provider.ProviderSlot
```

`SlotInstaller` copies the signed `package/` directory beside `slot.json` only
when the source sidecar is v3 package-aware and the package digest still
matches at copy time. v1/v2 installs remain manifest-only.

### Deterministic Digest

`package_tree_digest(package_dir)` returns:

```json
{
  "algorithm": "sha256_tree_v1",
  "layout": "directory",
  "file_count": 3,
  "value": "<sha256>"
}
```

The digest algorithm:

1. walks `package/`;
2. rejects symlinks, non-files, non-directories, escapes, and empty packages;
3. computes each file hash with chunked SHA-256 reads;
4. stores POSIX-normalized relative paths;
5. sorts by relative path;
6. canonical-JSON encodes the sorted file list with `sort_keys=True` and
   compact separators;
7. hashes that canonical file-list JSON.

mtime, permissions, owner, and platform directory ordering are intentionally not
part of the digest.

### v3 Sidecar

The v3 sidecar format is:

```json
{
  "schema_version": 3,
  "slot_id": "vendor.example",
  "key_id": "ops@v2",
  "algorithm": "ed25519",
  "signature": "<base64 Ed25519 signature>",
  "manifest_sha256": "<sha256 of canonical manifest JSON>",
  "package_digest": {
    "algorithm": "sha256_tree_v1",
    "layout": "directory",
    "file_count": 3,
    "value": "<sha256 tree hash>"
  }
}
```

`verify_slot_signature()` dispatches:

| Version | Result |
|---------|--------|
| v1 | Legacy ADR-0057 metadata; never `verified`. |
| v2 | Verified Ed25519 manifest-only signature; allowed for install/discovery, not execution. |
| v3 | Verified Ed25519 manifest plus package digest signature; required for provider execution. |

For v3, verification recomputes `package_tree_digest(manifest_dir / "package")`
before signature verification. Missing package dirs, malformed digest objects,
unknown digest algorithms, non-directory layouts, digest mismatch, and Ed25519
failures all return `invalid`.

### Resolve-Time Recheck And Import

`InstalledProviderSlot.resolve()` already repeated signature and revocation
verification before import. P7 keeps that recheck and adds the package digest to
the verified signature payload, closing the install/resolve time-of-check gap
for files under the signed package directory.

Provider execution eligibility now fails when the signature is verified v2 but
has no `package_digest`.

Provider imports no longer use arbitrary `sys.path` lookup. Bootstrap loads the
entrypoint module with `importlib.util.spec_from_file_location()` from:

```text
<installed slot dir>/package/
```

Intermediate packages use `submodule_search_locations` so relative helper
imports inside the signed package work. The loader path-confines module files
to the resolved `package/` root and temporarily disables bytecode writes during
provider import so `__pycache__` does not mutate the signed tree.

Transitive imports outside the signed package still resolve through normal
Python import mechanics. P7 signs the provider package, not its dependency
tree.

### Key Rotation Metadata

Signing keys remain free-form `key_id` values. Operators may use versioned ids
such as `ops@v1` and `ops@v2`.

`slot_signer_revocations` gains nullable `successor_key_id`. Revoking a key may
record the next key id for operator traceability:

```sql
successor_key_id TEXT
```

This is metadata only. P7 does not add validity windows, grace periods, remote
key discovery, or automatic trust rollover.

## Key Interfaces

- `doge.platform.slots.package_tree_digest(package_dir)`.
- `doge.platform.slots.sign_slot_manifest(..., package_dir=...)`.
- `doge slots sign <manifest> --key <pem> --package-dir <package>`.
- `SlotSignatureVerification.package_digest`.
- `ISlotSigningRepository.revoke(..., successor_key_id=...)`.
- `doge slots revoke-key <key_id> --successor-key-id <key_id>`.

## Alternatives Considered

### Alternative 1: Keep v2 manifest-only signatures for provider execution

- **Pros**: No migration friction.
- **Cons**: Leaves the signed-manifest-to-swapped-code attack intact.
- **Rejection Reason**: P7 exists specifically to bind the executed local
  package bytes to the trusted publisher signature.

### Alternative 2: Sign a tarball or wheel artifact

- **Pros**: Closer to common package distribution models.
- **Cons**: Adds artifact extraction, build metadata, and dependency semantics
  that do not exist in the current local alpha install surface.
- **Rejection Reason**: Directory tree hashing fits the current `slot.json`
  install preview and avoids adding a package manager in P7.

### Alternative 3: Sigstore or cosign

- **Pros**: Stronger publisher identity and supply-chain audit story.
- **Cons**: Requires online trust services or artifact distribution semantics
  that conflict with the local-first alpha boundary.
- **Rejection Reason**: ADR-0062 already rejected this for P3. P7 keeps
  Ed25519-only local verification and defers transparency logs to later
  distribution work.

### Alternative 4: Keep `importlib.import_module()` and only verify package hash

- **Pros**: Smaller implementation change.
- **Cons**: The verified package could still differ from the module imported
  from `sys.path`.
- **Rejection Reason**: Package identity is only meaningful if execution loads
  from the signed installed package directory.

## Consequences

### Positive

- Provider execution now requires package-aware identity, not only manifest
  identity.
- Tampering with signed package files after signing or after install fails
  closed before provider import.
- Discovery and install compatibility remain intact for v1/v2 sidecars.
- The import path used for provider execution is explicit and auditable.
- Rotation metadata gives operators a simple local record of successor keys.

### Negative

- v3 slots need a `package/` directory and must be re-signed when any package
  file changes.
- P7 still runs provider code in-process.
- Transitive pip dependencies are not signed by the slot sidecar.
- Bytecode writes are suppressed during provider import; code that relies on
  import-time bytecode output cannot use that behavior.
- Key rotation remains manual metadata, not a full key lifecycle system.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Operators mistake package identity for runtime containment | MEDIUM | HIGH | ADR/CDD/config/evidence repeat that P7 does not provide filesystem mediation, OS/container/WASM isolation, or malicious-code containment. |
| Tree hash drift across platforms | LOW | MEDIUM | Digest ignores mtime/perms, uses POSIX relative paths, sorts paths, and hashes file bytes only. |
| Package mutates during import | LOW | MEDIUM | Resolve-time verification runs before import and bytecode writes are disabled during provider load. P8 is needed for stronger runtime immutability. |
| Dependency confusion through transitive imports | MEDIUM | HIGH | Documented residual; P7 signs only the provider package and defers dependency tree signing. |

## CDD Requirements Addressed

| CDD System | Requirement | How This ADR Addresses It |
|------------|-------------|--------------------------|
| `design/cdd/p5-slot-provider-execution.md` | Provider execution must remain explicitly gated and locally auditable. | Makes v3 package-aware signatures a new provider-execution gate while keeping v2 manifest-only. |
| `design/cdd/p7-provider-package-identity.md` | Bind manifest, package digest, install copy, resolve-time recheck, and import path. | Defines the package layout, digest algorithm, v3 sidecar, installer behavior, and path-confined import mechanism. |
| `docs/progress/runtime-maturity.yaml` | Slot Platform maturity must remain experimental. | Records package identity as local alpha security hardening without changing maturity posture or external gates. |
| `C:\Users\WSMAN\.claude\plans\openclaw-rippling-sparkle.md` | P7 must close the manifest-only signing gap before P8 isolation work. | Requires v3 sidecars for provider execution and documents remaining P8 runtime isolation gaps. |

## Performance Implications

- **CPU**: SHA-256 over package files during signing, install verification, and
  resolve-time verification; Ed25519 verification remains one operation per
  signature check.
- **Memory**: bounded by 1 MB file read chunks plus the digest entry list.
- **I/O**: reads every file under `package/` when signing and verifying; copies
  `package/` during v3 install.
- **Network**: none.

## Migration Plan

1. Add deterministic package tree digest support.
2. Extend v2 sidecar dispatch to v3 package-aware signatures.
3. Add `--package-dir` to `doge slots sign`.
4. Copy verified package dirs during v3 install.
5. Require package-aware signatures for provider execution.
6. Replace arbitrary `sys.path` provider import with path-confined installed
   package loading.
7. Add `successor_key_id` revocation metadata.
8. Update ADR/CDD/config/registry/maturity/session/evidence records and P7
   tests.

## Validation Criteria

- v3 sidecars prove canonical manifest bytes plus deterministic package tree
  digest.
- v3 package-aware signatures are required for provider execution.
- v2 sidecars still verify for manifest-only install/discovery compatibility
  but do not unlock provider execution.
- Tampering with any signed package file before install or before resolve
  blocks execution.
- Provider entrypoints load from the installed signed package directory instead
  of arbitrary `sys.path`.
- Key revocation can record `successor_key_id`, and revoked keys still reject.
- Defaults remain conservative:
  `slot_install=false`, `slot_runtime_interception=false`, and
  `slot_provider_execution=false`.
- Maturity posture remains `production_ready: false`,
  `stable_declaration: forbidden`, and `level_3_sdk_platform: experimental`.

## Related Decisions

- ADR-0042: Slot Platform Foundation
- ADR-0057: Third-party Slot Install Preview
- ADR-0062: Slot Cryptographic Signing
- ADR-0063: Slot Runtime Permission Interception and Subprocess Hardening
- ADR-0064: Slot Provider Execution
- ADR-0066: Code-String Isolation Prototype and Contribution Residual
