# Sprint 046 - Slot Loader and Bundle Activation Manifest

> Sprint: 046 (Slot Loader and Bundle Activation)
> Date: 2026-07-07
> Status: Local implementation complete; local verification passed.

## Scope

This manifest records local evidence for the SlotLoader and bundle activation
sprint: JSON manifests can be loaded as manifest-only slots, and built-in
bundles can be activated for the current process behind
`DOGE_FEATURE_SLOT_LOADER`.

## Implementation Evidence

| Area | Evidence |
|---|---|
| ADR | `docs/architecture/adr-0056-slot-loader-bundle-activation.md` records the loader/activation decision. |
| CDD | `design/cdd/sprint-046-slot-loader-bundle-activation.md` records behavior, contracts, and acceptance criteria. |
| Loader contract | `src/doge/platform/slots/loader.py` adds `SlotLoader` and `ManifestOnlySlot`. |
| Activation contract | `src/doge/platform/slots/activation.py` adds `SlotBundleActivationState` and `policy_for_activation()`. |
| Feature flag | `src/doge/config/settings.py` adds `DOGE_FEATURE_SLOT_LOADER` lifecycle metadata and `FeatureConfig.slot_loader`. |
| Manifest dirs | `src/doge/config/settings.py` adds `SlotConfig.manifest_dirs` via `DOGE_SLOT_MANIFEST_DIRS`. |
| Capability discovery | `src/doge/application/capabilities/registry.py` exposes `feature.slot_loader`. |
| Bootstrap wiring | `src/doge/bootstrap/runtime_factories/slots.py` registers manifest-only slots and applies active bundle policy. |
| CLI | `src/doge/interfaces/cli/main.py` and `src/doge/interfaces/cli/commands/slots.py` add bundle list/activate commands. |
| API | `src/doge/interfaces/gateway/routers/slots.py` adds feature-gated bundle activation. |
| Route authority | `docs/API.md`, `docs/reference/http-api.md`, and `docs/registry/entities.yaml` track 96 HTTP routes. |
| Unit tests | `tests/unit/platform/slots/test_slot_loader.py` and `tests/unit/platform/slots/test_slot_activation.py` cover loader and activation contracts. |
| Contract tests | `tests/contract/test_slot_kernel_bundle_rows.py` and `tests/contract/test_slot_api.py` cover discovery and API activation. |
| CLI tests | `tests/cli/test_cli_slots.py` covers bundle parser/list/activation behavior. |
| Runtime maturity | `docs/progress/runtime-maturity.yaml` records Sprint 046 as local experimental only. |

## Verification Commands

```bash
py -3 -m pytest tests/test_settings.py tests/unit/use_cases/test_capability_registry.py tests/unit/platform/slots/test_slot_loader.py tests/unit/platform/slots/test_slot_activation.py tests/contract/test_slot_kernel_bundle_rows.py tests/contract/test_slot_api.py tests/cli/test_cli_slots.py tests/cli/test_doged_cli.py -q
py -3 -m pytest tests/unit/platform/slots tests/contract/test_tool_registry_slot_parity.py tests/contract/test_agent_backends_slot_parity.py tests/contract/test_workflow_slot_parity.py tests/contract/test_governance_slot_parity.py tests/contract/test_watcher_slot_parity.py tests/contract/test_document_slot_parity.py tests/contract/test_data_source_slot_parity.py tests/contract/test_gateway_slot_parity.py tests/contract/test_eval_slot_parity.py tests/contract/test_slot_kernel_bundle_rows.py tests/contract/test_slot_ui_registry.py tests/contract/test_slot_api.py -q
py -3 -m pytest tests/contract/test_api_doc_route_coverage.py tests/unit/governance/test_s017_planning_docs.py -q
py -3 tools/ci/sdk-contract-check.py
py -3 scripts/validate_import_boundaries.py
py -3 scripts/validate_docs_authority.py
py -3 scripts/validate_docs_links.py
py -3 scripts/validate_docs_maturity_claims.py
py -3 scripts/validate_alpha_maturity_honesty.py --file docs/architecture/adr-0056-slot-loader-bundle-activation.md
py -3 scripts/validate_alpha_maturity_honesty.py --file design/cdd/sprint-046-slot-loader-bundle-activation.md
py -3 scripts/validate_adr_index_completeness.py
py -3 scripts/validate_governance_yaml_shape.py
py -3 scripts/validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/openclaw-like-magical-barto.md
git diff --check
cmd.exe /c git diff --check
```

## Verification Results

| Gate | Result |
|---|---|
| Focused settings/capability/loader/activation/API/CLI/route-governance suite | Passed: 138 tests, 2 existing FastAPI deprecation warnings. |
| Broad slot parity suite | Passed: 167 tests, 2 existing FastAPI deprecation warnings. |
| API route coverage and route-governance sync | Passed: 39 tests, 2 existing FastAPI deprecation warnings. |
| SDK contract | Passed: 15 surfaces, 15 entity parity checks. |
| Import boundaries | Passed. |
| Docs authority | Passed. |
| Docs links | Passed: 114 markdown files validated. |
| Docs maturity claims | Passed. |
| ADR/CDD maturity guard | Passed for ADR-0056 and the Sprint 046 CDD. |
| ADR index / governance YAML | Passed. |
| Plan closure | Acceptable open: 2 passed, 4 operator-owned gates open, 0 failed, 0 invalid. |
| Whitespace | Passed with WSL `git diff --check` and Windows `git diff --check`. |

## Posture

- Production posture unchanged: `production_ready: false`,
  `stable_declaration: forbidden`, `level_3_sdk_platform: experimental`.
- No external/operator gates are closed by this sprint.
- No YAML parsing, provider entrypoint import, third-party install, signing,
  enterprise allowlist, persistent activation, SDK slot client, OS sandboxing,
  network interception, filesystem mediation, or database/secret interception
  is part of this sprint.
- Slot Platform remains experimental and feature-flagged off by default.
- Sprint 046 is a local loader/activation proof only; it does not complete the
  full OpenClaw-like Slot Platform.
