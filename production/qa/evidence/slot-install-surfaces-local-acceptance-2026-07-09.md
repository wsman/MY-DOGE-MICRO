# Slot Install Surfaces Local Acceptance Evidence

Date: 2026-07-09
Plan: `C:\Users\WSMAN\.claude\plans\openclaw-rippling-sparkle.md`
ADR: `docs/architecture/adr-0067-slot-install-surfaces.md`
CDD: `design/cdd/p9-install-surfaces.md`

## Status

Local acceptance evidence for P9 has passed in this worktree. The implementation
adds default-off HTTP, SDK, and Web install surfaces for the existing local slot
install workflow, plus rollback-safe install staging and explicit installed-slot
allowance under active built-in bundle policy.

Posture remains unchanged:

```yaml
production_ready: false
stable_declaration: forbidden
level_3_sdk_platform: experimental
```

External/operator gates remain open:

- S017-003
- W3-live
- AUTH-prod
- S017-007

## Delivered Scope

- `POST /v1/slots/install` local-path install route gated by `slot_install`.
- Enterprise `resource_type=slot`, `permission=write` ACL before mutation.
- Successful `slot_install` audit events through bootstrap install.
- `SlotInstaller` staged writes with cleanup on copy failure.
- Python SDK sync/async platform slot list, get, and install methods.
- TypeScript SDK platform slot list, get, and install methods.
- Web Slot Center install modal gated by `VITE_DOGE_FEATURE_SLOT_INSTALL_UI`.
- Explicit installed-slot ids allowed under active built-in bundle policy.
- Route authority count updated to 98 HTTP routes / 64 daemon-v1 routes.

## Preserved Deferrals

- `DOGE_FEATURE_SLOT_INSTALL` remains default off.
- `VITE_DOGE_FEATURE_SLOT_INSTALL_UI` remains default off.
- URL install, upload install, YAML manifests, marketplace/catalog behavior, and
  remote registry workflows remain deferred.
- SDK and Web clients call server endpoints only; they do not import providers or
  run install policy client-side.
- Provider execution remains separately gated by ADR-0064/0065 and is not made
  default-on.
- No filesystem mediation, malicious-code containment, OS/container/WASM
  sandboxing, remote CI promotion, external gate closure, or production maturity
  promotion is included.

## Verification Run

The following focused checks have passed in this local worktree:

```text
py -3 -m pytest tests\unit\platform\slots\test_slot_install.py tests\unit\platform\slots\test_slot_policy.py tests\unit\platform\slots\test_slot_bundle.py tests\unit\platform\slots\test_builtin_gateway_slot.py tests\contract\test_slot_kernel_bundle_rows.py tests\contract\test_slot_api.py tests\contract\test_api_doc_route_coverage.py tests\unit\governance\test_s017_planning_docs.py -q
=> 101 passed, 2 warnings

py -3 -m pytest tests\unit\platform\slots\test_slot_install.py tests\unit\platform\slots\test_slot_policy.py tests\unit\platform\slots\test_slot_bundle.py tests\contract\test_slot_kernel_bundle_rows.py tests\contract\test_slot_api.py -q
=> 60 passed, 2 warnings

py -3 tools\ci\sdk-contract-check.py
=> sdk-contract-check passed (18 surfaces, 15 entity parity checks)

npm test -- src\__tests__\client.spec.ts
=> 1 file passed, 18 tests passed

npm test -- src\stores\platform.spec.ts src\views\AdminCenterView.spec.ts
=> 2 files passed, 12 tests passed

npm run build
=> Web build passed

npm run build (packages/doge-sdk-typescript)
=> TypeScript SDK build passed
```

Governance validation:

```text
py -3 scripts\validate_alpha_maturity_honesty.py --file docs\progress\runtime-maturity.yaml
=> passed

py -3 scripts\validate_docs_maturity_claims.py
=> passed

py -3 scripts\validate_governance_yaml_shape.py
=> passed

py -3 scripts\validate_adr_index_completeness.py
=> passed

py -3 scripts\validate_plan_closure_gate.py --allow-open --source-plan C:\Users\WSMAN\.claude\plans\openclaw-rippling-sparkle.md
=> acceptable open, 2 passed / 4 open

git diff --check
=> passed

git diff --cached --check
=> passed

py -3 scripts\validate_docs_links.py
=> validated 125 markdown files

py -3 scripts\validate_docs_authority.py
=> passed
```

## Historical Evidence Policy

Older P0-P8 evidence files keep their at-acceptance statements such as "no HTTP
install API" and "no SDK install API." P9 supersedes those deferrals going
forward through ADR-0067 and this evidence file; historical acceptance records
are not rewritten.
