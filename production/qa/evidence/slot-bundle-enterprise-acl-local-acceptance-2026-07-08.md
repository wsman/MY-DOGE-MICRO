# Slot Bundle Enterprise ACL Local Acceptance - 2026-07-08

## Scope

P2.5 implements ADR-0061 for enterprise HTTP slot-bundle activate/deactivate
authorization:

- Enterprise-mode HTTP activation requires `enterprise_acl_grants` permission
  over `resource_type=slot_bundle`, the target bundle id, and `permission=write`.
- Enterprise-mode HTTP deactivation checks the current active bundle id with
  the same permission when an active bundle exists.
- Denied enterprise activation returns 403 before `slot_activation_state` writes
  and before `slot_bundle_activate` audit is appended.
- Granted activation/deactivation preserves ADR-0060 successful audit behavior.
- Wildcard grant behavior remains the existing enterprise governance repository
  contract: `resource_id=*` and/or `permission=*` may satisfy the check, while
  tenant and subject are exact.
- Local-demo HTTP behavior remains no-op-pass through `ensure_resource_access`.
- CLI activate/deactivate remains a local-operator trust path outside HTTP ACL
  checks.

## Boundaries

This evidence does not claim a schema migration, provider execution,
OS/container/WASM sandboxing, cryptographic slot signing, YAML manifests, HTTP
install API, SDK install API, marketplace behavior, install allowlist expansion,
remote CI, external gate closure, or maturity promotion.

Posture remains:

- `production_ready: false`
- `stable_declaration: forbidden`
- `level_3_sdk_platform: experimental`

## Verification

Focused P2.5 backend regression:

- `tests/contract/test_slot_api.py`
- `tests/integration/test_slot_bundle_activation_persistence.py`
- `tests/contract/test_enterprise_acl_api.py`
- `tests/unit/infrastructure/test_enterprise_governance_repository.py`
- `tests/cli/test_cli_slots.py`

Result: 64 passed, 2 warnings.

Full local gates:

- Python full regression: 2144 passed, 8 skipped, 128 warnings.
- Web suite: 168 passed.
- Web build: passed.
- TypeScript SDK: 17 passed; build passed.
- SDK contract: 15 surfaces, 15 entity parity checks.

Docs and governance validators:

- `scripts/validate_import_boundaries.py`: passed.
- `scripts/validate_docs_authority.py`: passed.
- `scripts/validate_docs_links.py`: validated 119 markdown files.
- `scripts/validate_docs_maturity_claims.py`: passed.
- `scripts/validate_adr_index_completeness.py`: passed.
- `scripts/validate_governance_yaml_shape.py`: passed.
- `scripts/validate_alpha_maturity_honesty.py --file C:/Users/WSMAN/.claude/plans/openclaw-rippling-sparkle.md`: passed.
- `scripts/validate_alpha_maturity_honesty.py --file docs/architecture/adr-0061-enterprise-bundle-acl.md`: passed.
- `scripts/validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/openclaw-rippling-sparkle.md`: acceptable-open, 2 passed / 4 open / 0 failed / 0 invalid.
- `git diff --check`: passed.
- `cmd.exe /c git diff --check`: passed.

Manual smoke:

- Enterprise HTTP no-grant activation returned 403, left active state false,
  and appended no slot-bundle audit event.
- Enterprise HTTP grant for `bundle.daemon_operator` allowed activate, then
  deactivate, and audit events were `slot_bundle_activate` and
  `slot_bundle_deactivate`.
- Local-demo HTTP activate/deactivate returned 200 through the helper's no-op
  local path.
- CLI activate/list/deactivate returned active true for `bundle.local_analyst`
  and then all inactive after deactivation.
- Admin Center generic alert path is covered by
  `web/src/views/AdminCenterView.spec.ts` with `slot_bundle access denied`.
