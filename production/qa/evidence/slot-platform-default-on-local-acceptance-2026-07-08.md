# Slot Platform Controlled Default-On Local Acceptance

Date: 2026-07-08
Plan: `C:\Users\WSMAN\.claude\plans\openclaw-rippling-sparkle.md`
ADR: `docs/architecture/adr-0058-slot-platform-controlled-default-on.md`

## Result

Local acceptance passed for P0 controlled default-on Slot Platform posture.

Default ON:

- `DOGE_FEATURE_WORKFLOW_TEMPLATES`
- `DOGE_FEATURE_SLOT_PLATFORM`
- `DOGE_FEATURE_SLOT_GOVERNANCE`
- `DOGE_FEATURE_SLOT_WATCHER`

Default OFF retained:

- `DOGE_FEATURE_SLOT_LOADER`
- `DOGE_FEATURE_SLOT_INSTALL`
- `DOGE_FEATURE_SLOT_ENFORCEMENT`
- `DOGE_FEATURE_SLOT_UI`
- `DOGE_FEATURE_PYTHON_ANALYSIS_ENABLED`
- `DOGE_FEATURE_RUNTIME_OUTBOX_PUBLISHER`
- `DOGE_FEATURE_PLATFORM_OBJECTS`
- `DOGE_FEATURE_CAPABILITY_REGISTRY`
- `DOGE_FEATURE_RUN_SUMMARY_API`

## Scope Invariants

- No push.
- No remote CI assertion.
- No `latest_remotely_verified_sha` promotion.
- No external/operator gate closure.
- No production-ready or stable declaration.
- No provider entrypoint import or third-party code execution.
- No OS/container/WASM sandboxing.
- No cryptographic slot signing format.
- No YAML manifest parser.
- No HTTP install API.
- No SDK install API.
- No marketplace.
- No persistent bundle activation.
- `slot_loader`, `slot_install`, `slot_enforcement`, `slot_ui`, and Python analysis remain default-off.

## Validation

Focused Python checks:

- `cmd.exe /c "set PYTHONPATH=src&& py -3 -m pytest tests/test_settings.py tests/cli/test_cli_slots.py tests/cli/test_doged_cli.py -q"` -> 70 passed, 2 warnings.
- `cmd.exe /c "set PYTHONPATH=src&& py -3 -m pytest tests/unit/platform/slots tests/unit/architecture/test_slot_boundary.py tests/unit/architecture/test_bootstrap_owns_factories.py -q"` -> 135 passed, 2 warnings.
- `cmd.exe /c "set PYTHONPATH=src&& py -3 -m pytest tests/contract/test_tool_registry_slot_parity.py tests/contract/test_agent_backends_slot_parity.py tests/contract/test_workflow_slot_parity.py tests/contract/test_governance_slot_parity.py tests/contract/test_watcher_slot_parity.py tests/contract/test_document_slot_parity.py tests/contract/test_data_source_slot_parity.py tests/contract/test_eval_slot_parity.py tests/contract/test_gateway_slot_parity.py tests/contract/test_slot_api.py tests/contract/test_slot_kernel_bundle_rows.py -q"` -> 62 passed, 2 warnings.
- `cmd.exe /c "set PYTHONPATH=src&& py -3 -m pytest tests/contract/test_platform_api.py tests/unit/infrastructure/test_platform_repository.py tests/unit/workspace_workflow/test_template_seed.py -q"` -> 23 passed, 2 warnings.
- `cmd.exe /c "set PYTHONPATH=src&& py -3 -m pytest tests/unit/use_cases/test_capability_registry.py -q"` -> 7 passed.

Full local gates:

- `cmd.exe /c "set PYTHONPATH=src&& py -3 -m pytest -q"` -> 2109 passed, 8 skipped, 128 warnings.
- `cmd.exe /c "cd web&& npm run test"` -> 164 passed.
- `cmd.exe /c "cd web&& npm run build"` -> passed.
- `cmd.exe /c "cd packages\doge-sdk-typescript&& npm test&& npm run build"` -> 17 passed; build passed.
- `cmd.exe /c "set PYTHONPATH=src&& py -3 tools/ci/sdk-contract-check.py"` -> passed, 15 surfaces / 15 entity parity checks.
- `cmd.exe /c "set PYTHONPATH=src&& py -3 scripts/validate_import_boundaries.py"` -> passed.
- `cmd.exe /c "set PYTHONPATH=src&& py -3 scripts/validate_docs_authority.py"` -> passed.
- `cmd.exe /c "set PYTHONPATH=src&& py -3 scripts/validate_docs_links.py"` -> validated 116 markdown files.
- `cmd.exe /c "set PYTHONPATH=src&& py -3 scripts/validate_docs_maturity_claims.py"` -> passed.
- `cmd.exe /c "set PYTHONPATH=src&& py -3 scripts/validate_adr_index_completeness.py"` -> passed.
- `cmd.exe /c "set PYTHONPATH=src&& py -3 scripts/validate_governance_yaml_shape.py"` -> passed.
- `cmd.exe /c "set PYTHONPATH=src&& py -3 scripts/validate_alpha_maturity_honesty.py --file C:/Users/WSMAN/.claude/plans/openclaw-rippling-sparkle.md"` -> passed.
- `cmd.exe /c "set PYTHONPATH=src&& py -3 scripts/validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/openclaw-rippling-sparkle.md"` -> acceptable-open: 2 passed, 4 open, 0 failed, 0 invalid.
- `git diff --check` -> passed.
- `cmd.exe /c git diff --check` -> passed.

Manual smoke:

- `cmd.exe /c "set PYTHONPATH=src&& py -3 -m doge.interfaces.cli slots list --json"` -> built-in slots resolved by default; `ui.research_workspace` remains disabled.
- `cmd.exe /c "set PYTHONPATH=src&& py -3 -m doge.interfaces.cli slots show market.core --json"` -> `market.core` manifest returned with 6 tool names.
- `cmd.exe /c "set PYTHONPATH=src&& py -3 -m doge.interfaces.cli slots bundle list --json"` -> bundles listed as inactive; default resolution does not activate bundles.
- `cmd.exe /c "set PYTHONPATH=src&& py -3 -m doge.interfaces.daemon.main features --json"` -> four promoted flags true; loader/install/enforcement/ui/Python analysis false.
- `cmd.exe /c "set PYTHONPATH=src&& set DOGE_FEATURE_SLOT_PLATFORM=0&& py -3 -m doge.interfaces.cli slots list --json"` -> `{"status": "disabled", "feature_flag": "DOGE_FEATURE_SLOT_PLATFORM"}`.

## Repairs During Validation

- Updated `tests/unit/use_cases/test_capability_registry.py` so lifecycle metadata asserts the authoritative `FEATURE_LIFECYCLES[*].current_default` instead of assuming every feature default is false.
- Updated `web/src/router/productNavigation.spec.ts` so the rollback redirect test mocks heavy lazy-loaded route components and validates the redirect itself without timing out on view transformation.

## Posture

`production_ready` remains false, `stable_declaration` remains forbidden, and
Level 3 SDK/platform maturity remains experimental. External/operator gates
`S017-003`, `W3-live`, `AUTH-prod`, and `S017-007` remain open.

## Post-P9 Supersession Note - 2026-07-09

This evidence is an at-acceptance historical record. Any "no HTTP install API",
"no SDK install API", "no SDK install method", or "no SDK slot client" wording
in this file remains true for the sprint accepted here. ADR-0067 and
`production/qa/evidence/slot-install-surfaces-local-acceptance-2026-07-09.md`
supersede that deferral going forward by adding default-off local HTTP, SDK, and
Web install surfaces. YAML manifests, URL/upload install, marketplace/catalog
behavior, default-on provider execution, external gate closure, and production
readiness remain deferred.
