# Sprint 047 - Third-party Slot Install Preview Manifest

> Sprint: 047 (Third-party Slot Install Preview)
> Date: 2026-07-07
> Status: Local implementation complete; local verification passed.

## Scope

This manifest records local evidence for the third-party slot install preview:
operators can install validated JSON manifests as manifest-only local slots,
while enterprise mode requires allowlist and trusted sidecar signature metadata.

## Implementation Evidence

| Area | Evidence |
|---|---|
| ADR | `docs/architecture/adr-0057-third-party-slot-install-preview.md` records the install preview decision. |
| CDD | `design/cdd/sprint-047-third-party-slot-install-preview.md` records behavior, contracts, and acceptance criteria. |
| Install contract | `src/doge/platform/slots/install.py` adds installer, policy, result, signature metadata verification. |
| Feature flag | `src/doge/config/settings.py` adds `DOGE_FEATURE_SLOT_INSTALL` lifecycle metadata and `FeatureConfig.slot_install`. |
| Install settings | `src/doge/config/settings.py` adds install dir, enterprise allowlist, trusted signers, and unsigned-local policy. |
| Capability discovery | `src/doge/application/capabilities/registry.py` exposes `feature.slot_install`. |
| Bootstrap wiring | `src/doge/bootstrap/runtime_factories/slots.py` adds `install_slot()` and install-dir manifest discovery. |
| CLI | `src/doge/interfaces/cli/main.py` and `src/doge/interfaces/cli/commands/slots.py` add `doge slots install`. |
| Unit tests | `tests/unit/platform/slots/test_slot_install.py` covers install and signature policy. |
| Contract tests | `tests/contract/test_slot_kernel_bundle_rows.py` covers installed manifest discovery. |
| CLI tests | `tests/cli/test_cli_slots.py` covers parser, disabled, and JSON install behavior. |
| Runtime maturity | `docs/progress/runtime-maturity.yaml` records Sprint 047 as local experimental only. |

## Verification Commands

```bash
py -3 -m pytest tests/unit/platform/slots/test_slot_install.py tests/test_settings.py tests/unit/use_cases/test_capability_registry.py tests/cli/test_cli_slots.py tests/contract/test_slot_kernel_bundle_rows.py -q
py -3 -m pytest tests/unit/platform/slots tests/contract/test_tool_registry_slot_parity.py tests/contract/test_agent_backends_slot_parity.py tests/contract/test_workflow_slot_parity.py tests/contract/test_governance_slot_parity.py tests/contract/test_watcher_slot_parity.py tests/contract/test_document_slot_parity.py tests/contract/test_data_source_slot_parity.py tests/contract/test_gateway_slot_parity.py tests/contract/test_eval_slot_parity.py tests/contract/test_slot_kernel_bundle_rows.py tests/contract/test_slot_ui_registry.py tests/contract/test_slot_api.py -q
py -3 tools/ci/sdk-contract-check.py
py -3 scripts/validate_import_boundaries.py
py -3 scripts/validate_docs_authority.py
py -3 scripts/validate_docs_links.py
py -3 scripts/validate_docs_maturity_claims.py
py -3 scripts/validate_alpha_maturity_honesty.py --file docs/architecture/adr-0057-third-party-slot-install-preview.md
py -3 scripts/validate_alpha_maturity_honesty.py --file design/cdd/sprint-047-third-party-slot-install-preview.md
py -3 scripts/validate_adr_index_completeness.py
py -3 scripts/validate_governance_yaml_shape.py
py -3 scripts/validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/openclaw-like-magical-barto.md
git diff --check
cmd.exe /c git diff --check
```

## Verification Results

| Gate | Result |
|---|---|
| Focused install/settings/capability/CLI/kernel suite | Passed: 65 tests. |
| Broad slot parity suite | Passed: 173 tests, with 2 known FastAPI deprecation warnings. |
| SDK contract | Passed: 15 surfaces, 15 entity parity checks. |
| Import boundaries | Passed. |
| Docs authority | Passed. |
| Docs links | Passed: 115 markdown files validated. |
| Docs maturity claims | Passed. |
| ADR/CDD maturity guard | Passed for ADR-0057 and this CDD. |
| ADR index / governance YAML | Passed. |
| Plan closure | Passed acceptable-open validation: 2 passed, 4 open, 0 failed, 0 invalid. |
| Whitespace | Passed WSL and Windows checks. |

## Posture

- Production posture unchanged: `production_ready: false`,
  `stable_declaration: forbidden`, `level_3_sdk_platform: experimental`.
- No external/operator gates are closed by this sprint.
- No provider entrypoint import, arbitrary Python execution, marketplace,
  cryptographic signature format, HTTP install route, SDK install method, YAML
  parser, OS sandboxing, network interception, filesystem mediation, or
  database/secret interception is part of this sprint.
- Slot Platform remains experimental and feature-flagged off by default.
