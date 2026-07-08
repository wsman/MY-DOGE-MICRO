# Slot Center Persistent Activation Local Acceptance - 2026-07-08

## Scope

P2 implements ADR-0060 for local Slot Center activation:

- `DOGE_FEATURE_SLOT_LOADER` defaults on.
- SQLite `slot_activation_state` stores one active built-in bundle record.
- Activation overwrites the active bundle; deactivation clears it.
- `SlotKernel` and bundle row construction hydrate the in-process activation
  cache from persistence.
- HTTP, CLI, and Web Slot Center expose activate/deactivate controls.
- Route authority tracks 97 HTTP routes.

## Boundaries

No bundle is auto-activated. This evidence does not claim provider execution,
OS/container/WASM sandboxing, cryptographic slot signing, YAML manifests, HTTP
install API, SDK install API, marketplace behavior, enterprise bundle ACL
policy, remote CI, external gate closure, or production readiness.

`production_ready` remains `false`, `stable_declaration` remains `forbidden`,
and Level 3 Slot Platform maturity remains experimental.

## Verification

Focused backend:

- `tests/unit/infrastructure/test_slot_activation_repository.py`
- `tests/integration/test_slot_bundle_activation_persistence.py`
- `tests/unit/platform/slots/test_slot_activation.py`
- `tests/unit/platform/slots/test_slot_loader.py`
- `tests/unit/infrastructure/test_migration_runner.py`
- `tests/contract/test_slot_kernel_bundle_rows.py`
- `tests/contract/test_slot_api.py`
- `tests/cli/test_cli_slots.py`
- `tests/cli/test_doged_cli.py`
- `tests/test_settings.py`

Result: 114 passed, 2 warnings.

Focused route/governance:

- `tests/contract/test_api_doc_route_coverage.py`
- `tests/unit/governance/test_s017_planning_docs.py`

Result: 39 passed, 2 warnings.

Focused architecture:

- `tests/unit/architecture/test_slot_boundary.py`
- `tests/unit/architecture/test_bootstrap_owns_factories.py`

Result: 26 passed.

Frontend:

- Focused Slot Center store/view suite: 8 passed.
- Full Web suite: 167 passed.
- Web build: passed.

Full local gates:

- Python full regression: 2138 passed, 8 skipped, 128 warnings.
- TypeScript SDK: 17 passed; build passed.
- SDK contract: 15 surfaces, 15 entity parity checks.

Docs and governance validators:

- `scripts/validate_import_boundaries.py`: passed.
- `scripts/validate_docs_authority.py`: passed.
- `scripts/validate_docs_links.py`: validated 118 markdown files.
- `scripts/validate_docs_maturity_claims.py`: passed.
- `scripts/validate_adr_index_completeness.py`: passed.
- `scripts/validate_governance_yaml_shape.py`: passed.
- `scripts/validate_alpha_maturity_honesty.py --file C:/Users/WSMAN/.claude/plans/openclaw-rippling-sparkle.md`: passed.
- `scripts/validate_alpha_maturity_honesty.py --file docs/architecture/adr-0060-persistent-slot-bundle-activation.md`: passed.
- `scripts/validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/openclaw-rippling-sparkle.md`: acceptable-open, 2 passed / 4 open / 0 failed / 0 invalid.
- `git diff --check`: passed.
- `cmd.exe /c git diff --check`: passed.

Manual smoke:

- With a temporary `DOGE_DB_DIR`, `doge slots bundle activate bundle.local_analyst --json` returned `status=activated` and `active_bundle_id=bundle.local_analyst`.
- `doge slots bundle list --json` showed `bundle.local_analyst.active=true`.
- `doge slots bundle deactivate --json` returned `status=deactivated` and `active_bundle_id=null`.
- A final bundle list showed all bundles inactive.
- `doged features --json` showed `slot_loader=true`, while `slot_install`, `slot_enforcement`, `slot_ui`, and `python_analysis_enabled` remained false.
