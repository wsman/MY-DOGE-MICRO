# Tool Slot Domain Migration Local Acceptance

Date: 2026-07-08
Plan: `C:\Users\WSMAN\.claude\plans\openclaw-rippling-sparkle.md`
ADR: `docs/architecture/adr-0059-tool-slot-domain-migration.md`

## Result

Local acceptance passed for P1 tool slot domain migration.

P1 adds five built-in `SlotType.TOOL` providers:

- `portfolio.core` with 4 portfolio/risk tools.
- `evidence.core` with 8 research/evidence/fundamental tools.
- `quant.lab` with 1 SQL query tool.
- `governance.actions` with 2 governed action tools.
- `compliance.screening` with 1 compliance screening tool.

Together with `market.core`'s 6 tools, 22 of the 23 tool descriptors are now
slot-owned in the default local Slot Platform path. `run_python_analysis`
remains intentionally outside slot ownership and retains its separate Python
analysis feature gate.

## Scope Invariants

- No push.
- No remote CI assertion.
- No `latest_remotely_verified_sha` promotion.
- No external/operator gate closure.
- No production-ready or stable declaration.
- No new feature flag, environment variable, OpenAPI surface, SDK public
  surface, persistence schema, or route surface.
- No provider code moved.
- No `ToolApplicationService` method body changed.
- No baseline `/v1/tools` fixture change.
- No provider entrypoint import or third-party code execution.
- No OS/container/WASM sandboxing.
- No cryptographic slot signing format.
- No YAML manifest parser.
- No HTTP install API.
- No SDK install API.
- No marketplace.
- No persistent bundle activation.
- `slot_loader`, `slot_install`, `slot_enforcement`, `slot_ui`, and Python
  analysis remain default-off.

## Validation

Focused Python checks:

- `cmd.exe /c "set PYTHONPATH=src&& py -3 -m pytest tests/unit/platform/slots/test_portfolio_slot.py tests/unit/platform/slots/test_evidence_slot.py tests/unit/platform/slots/test_quant_lab_slot.py tests/unit/platform/slots/test_governance_actions_slot.py tests/unit/platform/slots/test_compliance_screening_slot.py -q"` -> 20 passed.
- `cmd.exe /c "set PYTHONPATH=src&& py -3 -m pytest tests/contract/test_tool_registry_slot_parity.py -q"` -> 7 passed.
- `cmd.exe /c "set PYTHONPATH=src&& py -3 -m pytest tests/contract/test_slot_api.py tests/contract/test_slot_kernel_bundle_rows.py tests/cli/test_cli_slots.py tests/cli/test_doged_cli.py -q"` -> 64 passed, 2 warnings.
- `cmd.exe /c "set PYTHONPATH=src&& py -3 -m pytest tests/unit/architecture/test_slot_boundary.py tests/unit/architecture/test_bootstrap_owns_factories.py -q"` -> 26 passed.

Full local gates:

- `cmd.exe /c "set PYTHONPATH=src&& py -3 -m pytest -q"` -> 2130 passed, 8 skipped, 128 warnings.
- `cmd.exe /c "cd web&& npm run test"` -> 164 passed.
- `cmd.exe /c "cd web&& npm run build"` -> passed.
- `cmd.exe /c "cd packages\doge-sdk-typescript&& npm test&& npm run build"` -> 17 passed; build passed.
- `cmd.exe /c "set PYTHONPATH=src&& py -3 tools/ci/sdk-contract-check.py"` -> passed, 15 surfaces / 15 entity parity checks.
- `cmd.exe /c "set PYTHONPATH=src&& py -3 scripts/validate_import_boundaries.py"` -> passed.
- `cmd.exe /c "set PYTHONPATH=src&& py -3 scripts/validate_docs_authority.py"` -> passed.
- `cmd.exe /c "set PYTHONPATH=src&& py -3 scripts/validate_docs_links.py"` -> validated 117 markdown files.
- `cmd.exe /c "set PYTHONPATH=src&& py -3 scripts/validate_docs_maturity_claims.py"` -> passed.
- `cmd.exe /c "set PYTHONPATH=src&& py -3 scripts/validate_adr_index_completeness.py"` -> passed.
- `cmd.exe /c "set PYTHONPATH=src&& py -3 scripts/validate_governance_yaml_shape.py"` -> passed.
- `cmd.exe /c "set PYTHONPATH=src&& py -3 scripts/validate_alpha_maturity_honesty.py --file C:/Users/WSMAN/.claude/plans/openclaw-rippling-sparkle.md"` -> passed.
- `cmd.exe /c "set PYTHONPATH=src&& py -3 scripts/validate_alpha_maturity_honesty.py --file docs/architecture/adr-0059-tool-slot-domain-migration.md"` -> passed.
- `cmd.exe /c "set PYTHONPATH=src&& py -3 scripts/validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/openclaw-rippling-sparkle.md"` -> acceptable-open: 2 passed, 4 open, 0 failed, 0 invalid.
- `git diff --check` -> passed.
- `cmd.exe /c git diff --check` -> passed.

Manual smoke:

- `cmd.exe /c "set PYTHONPATH=src&& py -3 -m doge.interfaces.cli slots list --json"` -> 16 slot rows by default; the five P1 tool slots are `resolved` with tool counts 4, 8, 1, 2, and 1; `ui.research_workspace` remains disabled.
- `cmd.exe /c "set PYTHONPATH=src&& py -3 -m doge.interfaces.cli slots show portfolio.core --json"` -> manifest lists 4 tools and `risk_level=low`.
- `cmd.exe /c "set PYTHONPATH=src&& py -3 -m doge.interfaces.cli slots show evidence.core --json"` -> manifest lists 8 tools and `risk_level=low`.
- `cmd.exe /c "set PYTHONPATH=src&& py -3 -m doge.interfaces.cli slots show quant.lab --json"` -> manifest lists 1 tool and keeps Python analysis deferred in metadata.
- `cmd.exe /c "set PYTHONPATH=src&& py -3 -m doge.interfaces.cli slots show governance.actions --json"` -> manifest lists 2 tools and `risk_level=medium`.
- `cmd.exe /c "set PYTHONPATH=src&& py -3 -m doge.interfaces.cli slots show compliance.screening --json"` -> manifest lists 1 tool and `risk_level=low`.
- FastAPI `TestClient(create_app())` smoke -> `/v1/tools` returned 23 tools, `/v1/slots` returned 16 slots, and the five P1 slot rows resolved with tool counts 4, 8, 1, 2, and 1.
- `cmd.exe /c "set PYTHONPATH=src&& set DOGE_FEATURE_SLOT_PLATFORM=0&& py -3 -m doge.interfaces.cli slots list --json"` -> `{"status": "disabled", "feature_flag": "DOGE_FEATURE_SLOT_PLATFORM"}`.
- FastAPI slot-platform opt-out smoke -> `/v1/tools` still returned 23 tools and `/v1/slots` returned 404 because the slot discovery router is not mounted when the platform flag is off.
- `cmd.exe /c "set PYTHONPATH=src&& py -3 -m doge.interfaces.daemon.main features --json"` -> no new feature rows; `slot_platform`, `slot_governance`, and `slot_watcher` remain true, while `slot_loader`, `slot_install`, `slot_enforcement`, `slot_ui`, and `python_analysis_enabled` remain false.

## Review Notes

Static architecture review found no product/platform coupling violation and no
post-P0 execution surface broadening. The only risk called out was that
`portfolio.core` and `governance.actions` contain tools whose tool descriptors
remain high-risk or approval-required while the slot manifest risk metadata is
lower. ADR-0059 records this as an explicit governance risk: tool-level
`ToolDescriptor` category/metadata and entitlement policy remain the execution
authority; P1 slot manifest risk is discovery/grouping metadata only.

## Posture

`production_ready` remains false, `stable_declaration` remains forbidden, and
Level 3 SDK/platform maturity remains experimental. External/operator gates
`S017-003`, `W3-live`, `AUTH-prod`, and `S017-007` remain open.
