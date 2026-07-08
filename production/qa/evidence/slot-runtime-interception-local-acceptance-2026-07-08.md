# Slot Runtime Permission Interception Local Acceptance Evidence

Date: 2026-07-08
Plan: `C:\Users\WSMAN\.claude\plans\openclaw-rippling-sparkle.md`
ADR: `docs/architecture/adr-0063-slot-runtime-permission-interception.md`

## Verdict

PASS. P4 Slot Runtime Permission Interception is locally accepted. Remote CI was
not run and external/operator gates remain open.

## Scope

P4 adds default-off runtime interception and subprocess hardening:

- `DOGE_FEATURE_SLOT_RUNTIME_INTERCEPTION` defaults off and is separate from
  `DOGE_FEATURE_SLOT_ENFORCEMENT`.
- `SlotPermissionContext` carries the current slot id and `SlotPermissions`.
- Secret, database, and network guard wrappers enforce declared slot
  permissions for known ports when the flag is enabled and a slot context is
  active.
- Denied guarded access raises `SlotPermissionViolation` and emits best-effort
  `slot_permission_violation` audit metadata.
- Slot-aware tool, model, and data-source paths set slot context around runtime
  execution.
- `SubprocessCodeExecutor` scrubs secret-bearing env vars and runs from a
  scratch cwd.

## Non-Scope

No provider execution, filesystem mediation, OS/container/WASM sandboxing,
malicious-code containment, YAML manifest parser, HTTP install API, SDK install
API, marketplace behavior, external-gate closure, remote CI assertion,
`latest_remotely_verified_sha` promotion, or maturity promotion is included.

Posture remains:

```yaml
production_ready: false
stable_declaration: forbidden
level_3_sdk_platform: experimental
```

## Focused Verification

Runtime/subprocess/settings/capability suite:

```text
cmd.exe /c "set PYTHONPATH=src&& py -3 -m pytest tests\unit\platform\slots\test_slot_runtime_access.py tests\unit\capabilities\test_code_executor.py tests\test_settings.py tests\unit\use_cases\test_capability_registry.py -q"
53 passed
```

Slot boundary and parity suite:

```text
cmd.exe /c "set PYTHONPATH=src&& py -3 -m pytest tests\unit\architecture\test_slot_boundary.py tests\contract\test_tool_registry_slot_parity.py tests\contract\test_data_source_slot_parity.py tests\contract\test_agent_backends_slot_parity.py -q"
33 passed
```

Existing slot regression:

```text
cmd.exe /c "set PYTHONPATH=src&& py -3 -m pytest tests\unit\platform\slots\test_slot_enforcement.py tests\unit\platform\slots\test_slot_install.py tests\cli\test_cli_slots.py tests\contract\test_workflow_slot_parity.py tests\contract\test_governance_slot_parity.py tests\contract\test_watcher_slot_parity.py tests\contract\test_document_slot_parity.py tests\contract\test_gateway_slot_parity.py tests\contract\test_eval_slot_parity.py tests\contract\test_slot_ui_registry.py tests\contract\test_slot_api.py -q"
83 passed, 2 warnings
```

## Full Verification

Python full regression:

```text
cmd.exe /c "set PYTHONPATH=src&& py -3 -m pytest -q"
2167 passed, 8 skipped, 128 warnings
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

cmd.exe /c "set PYTHONPATH=src&& py -3 tools\ci\sdk-contract-check.py"
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
scripts/validate_alpha_maturity_honesty.py --file docs/architecture/adr-0063-slot-runtime-permission-interception.md
scripts/validate_alpha_maturity_honesty.py --file design/cdd/p4-slot-runtime-interception.md
scripts/validate_alpha_maturity_honesty.py --file docs/progress/runtime-maturity.yaml
scripts/validate_alpha_maturity_honesty.py --file production/qa/evidence/slot-runtime-interception-local-acceptance-2026-07-08.md
scripts/validate_alpha_maturity_honesty.py --file C:/Users/WSMAN/.claude/plans/openclaw-rippling-sparkle.md
```

Result: passed.

Plan closure:

```text
cmd.exe /c "set PYTHONPATH=src&& py -3 scripts\validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/openclaw-rippling-sparkle.md"
acceptable-open: 2 passed, 4 open, 0 failed, 0 invalid
```

Whitespace:

```text
cmd.exe /c "git diff --check"
git diff --check
```

Result: passed.

## Manual Smoke

Runtime guard smoke:

```text
flag_off_write saved
legacy_no_context_secret deepseek
db_read ['row']
db_write denied
secret_other denied
network_chat denied
audit [('db', 'write', 'save_rows', 'read'), ('secret', 'get_secret', 'deepseek.api_key', ('kimi.api_key',)), ('network', 'chat', 'chat', 'none')]
```

Subprocess hardening smoke:

```text
ok True
stdout ['None', 'C:\\Users\\WSMAN\\AppData\\Local\\Temp\\doge-python-analysis-aahjdjhr']
```

## Open Gates

- S017-003
- W3-live
- AUTH-prod
- S017-007
