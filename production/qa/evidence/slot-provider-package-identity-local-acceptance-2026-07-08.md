# Slot Provider Package Identity Local Acceptance Evidence

Date: 2026-07-08
Plan: `C:\Users\WSMAN\.claude\plans\openclaw-rippling-sparkle.md`
ADR: `docs/architecture/adr-0065-provider-package-identity.md`
CDD: `design/cdd/p7-provider-package-identity.md`

## Verdict

PASS. P7 Slot Provider Package Identity focused gate, migration gate,
architecture/API/docs gate, and governance validators passed locally. Remote CI
was not run and external/operator gates remain open.

## Scope

P7 adds local provider package identity for installed provider execution:

- v3 `slot.signature.json` sidecars bind canonical SlotManifest JSON bytes plus
  canonical deterministic `sha256_tree_v1` provider package digest bytes.
- `doge slots sign --package-dir <package>` writes v3 sidecars; without
  `--package-dir`, it keeps writing v2 manifest-only sidecars.
- `SlotInstaller` copies signed `package/` directories beside installed
  `slot.json` only for v3 package-aware installs.
- Provider execution requires verified v3 package-aware signatures; v2 sidecars
  remain install/discovery compatibility evidence only.
- Resolve-time verification recomputes the package digest before provider
  import.
- Provider import loads from the installed signed `package/` directory and not
  arbitrary `sys.path`.
- `slot_signer_revocations.successor_key_id` records local key successor
  metadata.

## Non-Scope

P7 is not malicious-code containment. It does not add filesystem mediation, raw
network denial, raw sqlite/subprocess/direct OS API containment,
OS/container/WASM sandboxing, transitive dependency signing, Sigstore/cosign,
HTTP install APIs, SDK install APIs, marketplace behavior, external-gate
closure, remote CI assertion, `latest_remotely_verified_sha` promotion, or
maturity promotion.

Posture remains:

```yaml
production_ready: false
stable_declaration: forbidden
level_3_sdk_platform: experimental
```

## Local Verification

Focused provider package identity, signing, repository, and CLI:

```text
cmd.exe /c "set PYTHONPATH=src&& py -3 -m pytest tests\unit\platform\slots\test_slot_install.py tests\unit\platform\slots\test_slot_provider_execution.py tests\unit\infrastructure\test_slot_signing_repository.py tests\cli\test_cli_slots.py -q"
=> 57 passed
```

Migration:

```text
cmd.exe /c "set PYTHONPATH=src&& py -3 -m pytest tests\unit\infrastructure\test_migration_runner.py -q"
=> 7 passed
```

Architecture/API slot regression:

```text
cmd.exe /c "set PYTHONPATH=src&& py -3 -m pytest tests\unit\architecture\test_slot_boundary.py tests\contract\test_slot_api.py tests\contract\test_slot_kernel_bundle_rows.py -q"
=> 44 passed, 2 known FastAPI deprecation warnings
```

Docs consistency:

```text
cmd.exe /c "set PYTHONPATH=src&& py -3 -m pytest tests\unit\governance\test_docs_consistency.py -q"
=> 7 passed
```

Governance validators:

```text
cmd.exe /c "set PYTHONPATH=src&& py -3 scripts\validate_import_boundaries.py"
cmd.exe /c "set PYTHONPATH=src&& py -3 scripts\validate_alpha_maturity_honesty.py --file docs\progress\runtime-maturity.yaml"
cmd.exe /c "set PYTHONPATH=src&& py -3 scripts\validate_alpha_maturity_honesty.py --file docs\architecture\adr-0065-provider-package-identity.md"
cmd.exe /c "set PYTHONPATH=src&& py -3 scripts\validate_alpha_maturity_honesty.py --file design\cdd\p7-provider-package-identity.md"
cmd.exe /c "set PYTHONPATH=src&& py -3 scripts\validate_alpha_maturity_honesty.py --file production\qa\evidence\slot-provider-package-identity-local-acceptance-2026-07-08.md"
cmd.exe /c "set PYTHONPATH=src&& py -3 scripts\validate_alpha_maturity_honesty.py --file C:\Users\WSMAN\.claude\plans\openclaw-rippling-sparkle.md"
cmd.exe /c "set PYTHONPATH=src&& py -3 scripts\validate_plan_closure_gate.py --allow-open --source-plan C:\Users\WSMAN\.claude\plans\openclaw-rippling-sparkle.md"
cmd.exe /c "set PYTHONPATH=src&& py -3 scripts\validate_docs_links.py"
cmd.exe /c "set PYTHONPATH=src&& py -3 scripts\validate_docs_maturity_claims.py"
cmd.exe /c "set PYTHONPATH=src&& py -3 scripts\validate_governance_yaml_shape.py"
cmd.exe /c "set PYTHONPATH=src&& py -3 scripts\validate_adr_index_completeness.py"
=> passed
```

Plan closure:

```text
cmd.exe /c "set PYTHONPATH=src&& py -3 scripts\validate_plan_closure_gate.py --allow-open --source-plan C:\Users\WSMAN\.claude\plans\openclaw-rippling-sparkle.md"
=> acceptable-open: 2 passed, 4 open, 0 failed, 0 invalid
```

Whitespace:

```text
cmd.exe /c "git diff --check"
git diff --check
=> passed
```

## Acceptance Invariants

- v3 package-aware sidecars are required for provider execution.
- v2 sidecars remain manifest-only.
- Provider code imports from the installed signed package dir.
- Tampering with signed package files blocks install or resolve.
- Feature defaults remain conservative.
- External gates remain open and maturity labels remain unchanged.

## Post-P9 Supersession Note - 2026-07-09

This evidence is an at-acceptance historical record. Any "no HTTP install API",
"no SDK install API", "no SDK install method", or "no SDK slot client" wording
in this file remains true for the sprint accepted here. ADR-0067 and
`production/qa/evidence/slot-install-surfaces-local-acceptance-2026-07-09.md`
supersede that deferral going forward by adding default-off local HTTP, SDK, and
Web install surfaces. YAML manifests, URL/upload install, marketplace/catalog
behavior, default-on provider execution, external gate closure, and production
readiness remain deferred.
