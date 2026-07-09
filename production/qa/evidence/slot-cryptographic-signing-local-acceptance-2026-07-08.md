# Slot Cryptographic Signing Local Acceptance Evidence

Date: 2026-07-08
Plan: `C:\Users\WSMAN\.claude\plans\openclaw-rippling-sparkle.md`
ADR: `docs/architecture/adr-0062-slot-cryptographic-signing.md`

## Verdict

PASS. P3 Slot Cryptographic Signing is locally accepted. Remote CI was not run
and external/operator gates remain open.

## Scope

P3 upgrades the manifest-only slot install preview signature mechanism:

- v2 `slot.signature.json` uses Ed25519 over canonical SlotManifest JSON bytes.
- Trusted publisher keys come from `DOGE_SLOT_TRUSTED_PUBLISHER_KEYS` and the
  optional `slot.trusted_publisher_keys` secret.
- SQLite `slot_signer_revocations` stores revoked signing key ids.
- `doge slots sign` writes v2 sidecars.
- `doge slots revoke-key` writes revocation state.
- v1 ADR-0057 sidecars remain readable as `legacy`, not `verified`.

## Non-Scope

No provider execution, OS/container/WASM sandboxing, YAML manifest parser, HTTP
install API, SDK install API, marketplace behavior, external-gate closure,
remote CI assertion, `latest_remotely_verified_sha` promotion, or maturity
promotion is included.

Posture remains:

```yaml
production_ready: false
stable_declaration: forbidden
level_3_sdk_platform: experimental
```

## Focused Verification

```text
cmd.exe /c "set PYTHONPATH=src&& py -3 -m pytest tests/unit/platform/slots/test_slot_install.py tests/unit/infrastructure/test_slot_signing_repository.py tests/unit/infrastructure/test_migration_runner.py tests/test_settings.py tests/cli/test_cli_slots.py -q"
```

Result:

```text
70 passed
```

## Full Verification

Python full regression:

```text
cmd.exe /c "set PYTHONPATH=src&& py -3 -m pytest -q"
2155 passed, 8 skipped, 128 warnings
```

Web suite and build:

```text
npm run test
37 files passed, 168 tests passed

npm run build
passed
```

TypeScript SDK and SDK contract:

```text
npm run test
17 passed

npm run build
passed

cmd.exe /c "set PYTHONPATH=src&& py -3 tools/ci/sdk-contract-check.py"
sdk-contract-check passed (15 surfaces, 15 entity parity checks)
```

Governance validators:

```text
scripts/validate_import_boundaries.py
scripts/validate_docs_authority.py
scripts/validate_docs_links.py
scripts/validate_docs_maturity_claims.py
scripts/validate_governance_yaml_shape.py
scripts/validate_adr_index_completeness.py
scripts/validate_alpha_maturity_honesty.py --file docs/architecture/adr-0062-slot-cryptographic-signing.md
scripts/validate_alpha_maturity_honesty.py --file docs/architecture/adr-0057-third-party-slot-install-preview.md
scripts/validate_alpha_maturity_honesty.py --file design/cdd/sprint-047-third-party-slot-install-preview.md
scripts/validate_alpha_maturity_honesty.py --file docs/progress/runtime-maturity.yaml
scripts/validate_alpha_maturity_honesty.py --file production/qa/evidence/slot-cryptographic-signing-local-acceptance-2026-07-08.md
scripts/validate_alpha_maturity_honesty.py --file C:/Users/WSMAN/.claude/plans/openclaw-rippling-sparkle.md
```

Result: passed.

Plan closure:

```text
cmd.exe /c "set PYTHONPATH=src&& py -3 scripts/validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/openclaw-rippling-sparkle.md"
acceptable-open: 2 passed, 4 open, 0 failed, 0 invalid
```

Whitespace:

```text
cmd.exe /c "git diff --check"
git diff --check
```

Result: both passed.

## Manual Smoke

Temporary local slot smoke covered:

- `doge slots sign` wrote a v2 Ed25519 sidecar.
- `doge slots install` reported `signature.status=verified`.
- Tampering the manifest after signing was rejected as invalid.
- `doge slots revoke-key ops` wrote revocation state and later install was
  rejected as revoked.
- A v1 metadata sidecar installed locally as `legacy` with the expected warning.

Smoke summary:

```json
{
  "install_signature": "verified",
  "legacy_status": "legacy",
  "revoked_rejected": true,
  "signed": "signed",
  "tamper_rejected": true
}
```

## Open Gates

- S017-003
- W3-live
- AUTH-prod
- S017-007

## Post-P9 Supersession Note - 2026-07-09

This evidence is an at-acceptance historical record. Any "no HTTP install API",
"no SDK install API", "no SDK install method", or "no SDK slot client" wording
in this file remains true for the sprint accepted here. ADR-0067 and
`production/qa/evidence/slot-install-surfaces-local-acceptance-2026-07-09.md`
supersede that deferral going forward by adding default-off local HTTP, SDK, and
Web install surfaces. YAML manifests, URL/upload install, marketplace/catalog
behavior, default-on provider execution, external gate closure, and production
readiness remain deferred.
