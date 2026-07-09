# ADR-0062: Slot Cryptographic Signing

## Status

Accepted

## Date

2026-07-08

## Decision Makers

wsman (product owner) / implementation agent

## Summary

P3 upgrades the Slot install preview signature mechanism from ADR-0057's
metadata-only sidecar to Ed25519 cryptographic verification over canonical JSON
manifest bytes.

The decision adds:

- v2 `slot.signature.json` sidecars with `key_id`, `algorithm=ed25519`,
  `signature`, and canonical `manifest_sha256`;
- trusted publisher public keys from `DOGE_SLOT_TRUSTED_PUBLISHER_KEYS` and the
  canonical secret `slot.trusted_publisher_keys`;
- SQLite-backed key revocation through `slot_signer_revocations`;
- CLI signing and revocation commands:
  - `doge slots sign <manifest> --key <private-key-PEM-path> [--key-id <id>]`;
  - `doge slots revoke-key <key_id> [--reason <text>]`;
- legacy handling for ADR-0057 v1 metadata sidecars.

This ADR releases only the previous "no cryptographic signing format"
invariant. It does not by itself enable provider entrypoint execution,
sandboxing, YAML manifests, HTTP install APIs, SDK install APIs, marketplace
behavior, external gate closure, remote CI promotion, or maturity promotion.
`slot_install` remains default off.

ADR-0064 later consumes this ADR's verified Ed25519 signature and revocation
checks as required gates for a separate default-off installed-provider execution
path. Signing alone still does not make a slot execution eligible.

Status Update - 2026-07-08: ADR-0065 extends this ADR with v3 package-aware
sidecars for provider execution. v2 sidecars remain manifest-only and still
verify for install/discovery compatibility, but v3 signs canonical manifest
bytes plus a deterministic provider package digest and is now required before
installed provider execution can import code.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python 3.10+; `cryptography==44.0.2`; SQLite; existing CLI and Slot install preview |
| **Domain** | Security / Slot Platform install preview / CLI operator controls |
| **Knowledge Risk** | MEDIUM - cryptographic sidecar verification and key revocation semantics |
| **References Consulted** | `docs/reference/python/VERSION.md`, `standards/technical-preferences.md`, `docs/architecture/adr-0057-third-party-slot-install-preview.md`, `docs/architecture/adr-0060-persistent-slot-bundle-activation.md`, `C:\Users\WSMAN\.claude\plans\openclaw-rippling-sparkle.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | Ed25519 install unit tests, revocation repository tests, CLI sign/revoke tests, settings tests, migration registry tests, docs/governance validators, alpha maturity honesty, acceptable-open plan closure, whitespace checks |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0057 (Third-party Slot Install Preview), ADR-0060 (Persistent Slot Bundle Activation) |
| **Extends** | ADR-0057 by upgrading slot signature verification to Ed25519, trusted publisher keys, and revocation |
| **Supersedes** | ADR-0057's metadata-only signature decision for new v2 sidecars; v1 sidecars remain readable as `legacy` |
| **Enables** | Later provider-execution trust decisions after sandboxing and stronger permission mediation exist |
| **Blocks** | Any claim that cryptographic manifest signing alone permits provider execution, OS/container/WASM sandboxing, marketplace install, HTTP install, SDK install, external gate closure, or production maturity promotion |
| **Ordering Note** | ADR-0057 remains the install-preview decision. This ADR upgrades only the signature mechanism and revocation state behind the same feature flag. |

## Context

ADR-0057 intentionally shipped a manifest-only install preview. Its v1 sidecar
validated `slot_id`, a raw-file SHA-256 digest, and a trusted signer string. It
was explicitly documented as metadata validation, not cryptographic signing.

That was the right Sprint 047 boundary because there was no sandbox, no
provider execution, and no key-management story. P3 needs a stronger install
trust primitive before any later execution decision can be evaluated.

The project already carries `PyJWT[crypto]` for enterprise JWT verification, so
the `cryptography` package is already part of the practical runtime footprint.
P3 directly pins `cryptography==44.0.2` to make that dependency explicit and
adds it to the allowed-library register.

## Constraints

- Keep `DOGE_FEATURE_SLOT_INSTALL` default `false`.
- Keep manifest-only install behavior; do not import provider entrypoints.
- Keep local-demo unsigned install possible through
  `DOGE_SLOT_ALLOW_UNSIGNED_LOCAL`.
- Enterprise install must require a verified v2 cryptographic signature.
- v1 metadata sidecars must not be reported as verified.
- Do not add key generation, remote key distribution, Sigstore, cosign,
  container/WASM sandboxing, HTTP install APIs, SDK install APIs, YAML parsing,
  or marketplace behavior in P3.
- Preserve `production_ready: false`, `stable_declaration: forbidden`, and
  `level_3_sdk_platform: experimental`.

## Decision

Use Ed25519 signatures over canonical JSON manifest bytes.

Canonical bytes are:

```python
json.dumps(
    manifest_dict,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=False,
).encode("utf-8")
```

The v2 sidecar format is:

```json
{
  "schema_version": 2,
  "slot_id": "local.example",
  "key_id": "ops",
  "algorithm": "ed25519",
  "signature": "<base64 Ed25519 signature over canonical manifest bytes>",
  "manifest_sha256": "<sha256 of canonical manifest bytes>"
}
```

`verify_slot_signature()` now returns one of:

| Status | Meaning |
|--------|---------|
| `missing` | No sidecar exists. Local demo may warn; enterprise rejects. |
| `invalid` | Sidecar is malformed, manifest hash mismatches, or Ed25519 verification fails. |
| `legacy` | ADR-0057 v1 metadata sidecar is syntactically valid but not cryptographic. |
| `untrusted` | v2 sidecar key id is not present in the trusted publisher key map. |
| `revoked` | v2 sidecar key id is trusted but is listed in `slot_signer_revocations`. |
| `verified` | v2 sidecar uses a trusted, non-revoked Ed25519 public key and verifies over canonical manifest bytes. |

`SlotSignatureVerification.verified` remains `status == "verified"`.

Trusted publisher keys are configured as CSV pairs:

```text
DOGE_SLOT_TRUSTED_PUBLISHER_KEYS=ops=<base64-public-key>,sec=<base64-public-key>
```

The same pair format is also accepted from the canonical secret
`slot.trusted_publisher_keys` through `ISecretProvider`. The legacy
`DOGE_SLOT_TRUSTED_SIGNERS` setting remains only for v1 metadata compatibility.

Key revocation is stored in SQLite:

```sql
CREATE TABLE IF NOT EXISTS slot_signer_revocations (
    key_id TEXT PRIMARY KEY,
    revoked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reason TEXT,
    actor_hash TEXT
);
```

The port is `ISlotSigningRepository` with:

- `is_revoked(key_id) -> bool`;
- `revoke(key_id, reason, actor_hash)`;
- `list_revoked()`.

The SQLite implementation follows the existing slot activation repository
pattern and is injected into the install policy from bootstrap wiring.

## Alternatives Considered

### Alternative 1: Keep v1 metadata sidecars as verified

- **Description**: Preserve ADR-0057 v1 behavior and keep trusted signer strings
  as sufficient for enterprise install.
- **Pros**: No migration friction for existing local manifests.
- **Cons**: Continues to treat writable JSON metadata as trust evidence.
- **Rejection Reason**: P3 intentionally releases the no-cryptographic-signing
  invariant. v1 sidecars remain readable but are downgraded to `legacy`.

### Alternative 2: Sigstore or cosign

- **Description**: Use transparency-log or artifact-signing workflows.
- **Pros**: Stronger publisher identity and supply-chain story.
- **Cons**: Requires online services, package artifacts, or container-style
  distribution that the local-first alpha platform does not yet have.
- **Rejection Reason**: P3 needs local deterministic verification without
  marketplace/package infrastructure.

### Alternative 3: Require signatures in local demo mode

- **Description**: Reject all unsigned manifests now that v2 signatures exist.
- **Pros**: Stronger local default.
- **Cons**: Blocks the existing local preview workflow and changes ADR-0057's
  operator ergonomics more than P3 requires.
- **Rejection Reason**: Local demo may still allow unsigned manifests with a
  warning. Enterprise mode fails closed on anything other than verified v2.

## Consequences

### Positive

- Slot install preview now has a real cryptographic manifest-signing format.
- Enterprise install can distinguish verified, legacy, untrusted, revoked, and
  malformed sidecars.
- Key revocation is persistent and testable through the same SQLite migration
  pattern as other local operator state.
- CLI operators can sign and revoke keys without adding remote install APIs.

### Negative

- Key distribution and rotation remain manual.
- P3 v2 signatures cover only the manifest. ADR-0065 adds v3 package-aware
  sidecars for installed provider execution, but transitive dependency signing
  remains out of scope.
- v1 metadata sidecars must be re-signed to satisfy enterprise install.
- `cryptography` is now a direct project dependency.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Operators treat manifest signing as permission to execute third-party code | MEDIUM | HIGH | ADR, maturity notes, and evidence repeat that provider execution and sandboxing remain absent. |
| Canonical JSON mismatch invalidates signatures after manual edits | MEDIUM | MEDIUM | Canonicalization is pinned and tested; CLI signs the exact manifest object. |
| Revoked key cache expectations emerge | LOW | MEDIUM | Verification queries the repository directly in local alpha; no caching contract is introduced. |
| Legacy v1 sidecars are misunderstood | MEDIUM | MEDIUM | v1 status is `legacy`, not `verified`, and local installs warn. |

## CDD Requirements Addressed

| CDD System | Requirement | How This ADR Addresses It |
|------------|-------------|--------------------------|
| `design/cdd/sprint-047-third-party-slot-install-preview.md` | Enterprise install preview must fail closed. | Enterprise mode now requires verified v2 Ed25519 signatures in addition to allowlist policy. |
| `docs/progress/runtime-maturity.yaml` | Slot Platform maturity must remain experimental. | P3 records cryptographic manifest signing without changing maturity posture or external gates. |
| `C:\Users\WSMAN\.claude\plans\openclaw-rippling-sparkle.md` | P3 must add trusted publisher keys and revocation. | Adds trusted key parsing, secret-provider support, SQLite revocation, and CLI revoke. |

## Performance Implications

- **CPU**: one Ed25519 verification and canonical JSON digest per signed
  manifest install or signature check.
- **Memory**: negligible, bounded by manifest size.
- **I/O**: reads manifest and sidecar; revocation checks read SQLite local
  state; revoke writes one SQLite row.
- **Network**: none.

## Migration Plan

1. Add v2 Ed25519 verification and signing helpers.
2. Extend slot install settings with trusted publisher keys.
3. Add the signing-key revocation port, SQLite adapter, migration, schema, and
   migration manifests.
4. Inject trusted keys and revocation repository through bootstrap install
   policy wiring.
5. Add CLI `slots sign` and `slots revoke-key`.
6. Downgrade v1 sidecars to `legacy`.
7. Update tests, configuration docs, maturity records, ADR registry, source
   plan, and local acceptance evidence.

## Validation Criteria

- `slot_install` remains default off.
- v2 Ed25519 sidecars verify only when signed over canonical manifest bytes by
  a trusted, non-revoked key.
- Tampered manifests and signatures are invalid.
- Untrusted keys produce `untrusted`.
- Revoked keys produce `revoked` and are rejected.
- v1 sidecars produce `legacy` and do not satisfy enterprise install.
- CLI sign writes a v2 sidecar.
- CLI revoke writes `slot_signer_revocations`.
- ADR-0065 later adds v3 package-aware signatures for provider execution; this
  P3 decision by itself adds no provider execution, sandboxing, HTTP install,
  SDK install, YAML parser, marketplace, external gate closure, or maturity
  promotion.
- Maturity posture remains `production_ready: false`,
  `stable_declaration: forbidden`, and `level_3_sdk_platform: experimental`.

## Related Decisions

- ADR-0042: Slot Platform Foundation
- ADR-0055: Slot Permission and Health Enforcement
- ADR-0057: Third-party Slot Install Preview
- ADR-0060: Persistent Slot Bundle Activation
- ADR-0065: Provider Package Identity
