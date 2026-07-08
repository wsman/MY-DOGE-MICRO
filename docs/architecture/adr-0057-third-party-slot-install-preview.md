# ADR-0057: Third-party Slot Install Preview

## Status

Accepted

## Status Update - 2026-07-08

ADR-0062 supersedes only this ADR's metadata-only signature mechanism. Sprint
047 remains the install-preview decision: installs are still manifest-only,
`DOGE_FEATURE_SLOT_INSTALL` remains default off, and default discovery still
does not import provider entrypoints. New v2 sidecars use Ed25519 cryptographic
signatures over canonical manifest bytes; v1 sidecars from this ADR remain
readable as `legacy` and do not satisfy enterprise verified-signature policy.

ADR-0064 later supersedes the blanket "provider entrypoints are not imported or
executed" statement only for an explicit, default-off, installed,
trusted-publisher, revocation-checked, runtime-intercepted local alpha path.
ADR-0057 remains accurate for install preview and manifest-only discovery.

## Date

2026-07-07

## Decision Makers

wsman (product owner) / implementation agent

## Summary

Sprint 047 adds a controlled local install preview for non-built-in slots.
`doge slots install <source>` validates one JSON SlotManifest, checks declared
permissions, optional sidecar signature metadata, and enterprise allowlist
policy, then copies the manifest into the configured local slot install
directory as a manifest-only slot.

The install preview never imports the manifest entrypoint and never executes
third-party Python code. Installed slots are discovered only when
`DOGE_FEATURE_SLOT_PLATFORM=1`, `DOGE_FEATURE_SLOT_LOADER=1`, and
`DOGE_FEATURE_SLOT_INSTALL=1`.

This sprint does not add a marketplace, cryptographic signature format,
provider execution, SDK slot client, HTTP install route, YAML parser, or OS
sandbox.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python 3.10+; stdlib JSON/hashlib/shutil; existing CLI and SlotLoader |
| **Domain** | Security / CLI / Slot Platform install preview |
| **Knowledge Risk** | MEDIUM - local install policy and enterprise fail-closed behavior |
| **References Consulted** | `docs/reference/python/VERSION.md`, `docs/architecture/adr-0042-slot-platform.md`, `docs/architecture/adr-0055-slot-enforcement.md`, `docs/architecture/adr-0056-slot-loader-bundle-activation.md`, `C:\Users\WSMAN\.claude\plans\openclaw-like-magical-barto.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | Slot install unit tests, CLI install tests, settings/capability tests, broad slot parity, import/docs/maturity validators |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0042 (Slot Platform Foundation), ADR-0055 (Slot Permission and Health Enforcement), ADR-0056 (Slot Loader and Bundle Activation) |
| **Extends** | ADR-0056 by adding a manifest-only install preview and installed manifest discovery |
| **Supersedes** | None |
| **Enables** | Future provider-entrypoint execution decision, cryptographic signing, sandbox implementation |
| **Blocks** | Third-party provider execution until an explicit sandbox/signing ADR exists |

## Context

The platform can load JSON manifests and activate built-in bundles, but it still
needs a safe way to preview local third-party slot installation. Loading and
executing arbitrary Python would create the exact OpenClaw-style risk the slot
plan is trying to avoid. The next step must therefore separate installation of
the manifest contract from execution of provider code.

The existing manifest loader and enforcement guard provide the boundary:
installation can validate the manifest, permission declarations, signature
metadata, and enterprise allowlist, while keeping runtime contributions empty
through `ManifestOnlySlot`.

## Constraints

- Keep `DOGE_FEATURE_SLOT_INSTALL` default `false`.
- Require `DOGE_FEATURE_SLOT_PLATFORM=1` and `DOGE_FEATURE_SLOT_LOADER=1`.
- Install one manifest at a time from a JSON file or directory containing
  `slot.json`.
- Copy manifests into `DOGE_SLOT_INSTALL_DIR`.
- Preserve manifest-only behavior; do not import provider entrypoints.
- Reject `risk_level=forbidden`, high-risk slots by default, and shell
  permission by default.
- Local demo mode may allow unsigned manifests with an explicit warning.
- Enterprise mode must require allowlist membership, configured trusted
  signers, and verified sidecar signature metadata.
- Do not add HTTP install endpoints, SDK install methods, YAML parsing, or OS
  sandboxing in this sprint.

## Decision

Add `doge.platform.slots.install` with:

- `SlotInstallPolicy`;
- `SlotSignatureVerification`;
- `SlotInstallResult`;
- `SlotInstaller`;
- `verify_slot_signature()`.

The sidecar signature metadata is JSON:

```json
{
  "schema_version": 1,
  "slot_id": "local.example",
  "manifest_sha256": "...",
  "signer": "ops"
}
```

This is local-alpha metadata validation, not a cryptographic signature format.
It verifies that the sidecar belongs to the manifest, that the manifest digest
matches, and that the signer is trusted when policy requires trust.

Add settings:

- `DOGE_FEATURE_SLOT_INSTALL`;
- `DOGE_SLOT_INSTALL_DIR`;
- `DOGE_SLOT_ENTERPRISE_ALLOWLIST`;
- `DOGE_SLOT_TRUSTED_SIGNERS`;
- `DOGE_SLOT_ALLOW_UNSIGNED_LOCAL`.

Add `install_slot()` in bootstrap runtime slot factories. It gates install on
slot platform, loader, and install feature flags, builds policy from settings,
and calls `SlotInstaller`.

Add CLI:

```bash
doge slots install ./my_slot --json
```

Installed manifests are included in manifest-only discovery by
`build_builtin_slot_registry()` only when the install flag is enabled and the
install directory exists.

## Alternatives Considered

### Alternative 1: Execute provider entrypoints after install

- **Description**: Import `entrypoint` after successful manifest install.
- **Pros**: More complete plugin behavior.
- **Cons**: Executes third-party Python without a sandbox or cryptographic
  trust root.
- **Rejection Reason**: Provider execution is explicitly blocked until a
  separate sandbox/signing decision exists.

### Alternative 2: Expose HTTP install API

- **Description**: Add `POST /v1/slots/install`.
- **Pros**: Web/SDK operators could install slots remotely.
- **Cons**: Adds a high-risk write operation to the daemon surface before
  enterprise auth and allowlist policy are production-proven.
- **Rejection Reason**: Sprint 047 keeps install local CLI only.

### Alternative 3: Require signatures in local demo mode

- **Description**: Reject all unsigned local manifests.
- **Pros**: Stronger default posture.
- **Cons**: Blocks local development preview before a real signing format
  exists.
- **Rejection Reason**: Local demo may allow unsigned manifests but emits an
  explicit warning; enterprise mode remains fail-closed.

## Consequences

### Positive

- Third-party local preview has a controlled path without code execution.
- Enterprise mode defaults to allowlist + trusted signer requirements.
- Installed manifests can be discovered through existing `/v1/slots` and CLI
  status rows when flags are enabled.
- Future provider execution has a clear gate to extend.

### Negative

- Installed slots do not contribute runtime behavior yet.
- Sidecar signature metadata is not a cryptographic signature.
- Install state is file-based local state under one configured directory.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Operators mistake metadata signatures for cryptographic signing | MEDIUM | HIGH | ADR/CDD/docs call it local-alpha metadata only. |
| Installed manifest shadows a built-in slot id | LOW | MEDIUM | `SlotRegistry.register()` still rejects duplicate ids. |
| Install writes outside intended location | LOW | MEDIUM | Destination is derived from validated slot id under `DOGE_SLOT_INSTALL_DIR`. |

## CDD Requirements Addressed

| CDD System | Requirement | How This ADR Addresses It |
|------------|-------------|--------------------------|
| `design/cdd/sprint-047-third-party-slot-install-preview.md` | Local third-party slot preview must not execute provider code. | Installs manifest-only JSON records and preserves `ManifestOnlySlot` behavior. |
| `design/cdd/sprint-047-third-party-slot-install-preview.md` | Enterprise mode must fail closed. | Requires allowlist, trusted signer configuration, and verified signature metadata. |
| `docs/progress/runtime-maturity.yaml` | Slot Platform maturity remains experimental. | Records Sprint 047 as local experimental only. |

## Performance Implications

- **CPU**: one manifest validation and SHA-256 digest per install.
- **Memory**: no long-lived memory beyond registry discovery rows.
- **I/O**: copies manifest and optional signature sidecar into
  `DOGE_SLOT_INSTALL_DIR`.
- **Network**: none.

## Migration Plan

1. Add pure install preview contracts.
2. Add feature flag and install policy settings.
3. Add bootstrap `install_slot()` helper.
4. Include install directory in manifest-only discovery when install flag is on.
5. Add CLI `doge slots install`.
6. Add focused unit/CLI/contract tests.
7. Update governance docs and roadmap.

## Validation Criteria

- Install flag defaults off.
- Local unsigned install copies one manifest and reports a warning.
- High-risk, forbidden-risk, and shell-permission slots are rejected by default.
- Enterprise install requires allowlist and trusted signature metadata.
- Invalid signature metadata is rejected.
- Installed manifests appear in slot status rows when install flag is enabled.
- Existing built-in slot parity remains unchanged.
- Maturity posture remains `production_ready: false`,
  `stable_declaration: forbidden`, and `level_3_sdk_platform: experimental`.

## Related Decisions

- ADR-0042: Slot Platform Foundation
- ADR-0055: Slot Permission and Health Enforcement
- ADR-0056: Slot Loader and Bundle Activation
