# Sprint 044 - UI Slot Consumer Manifest

> Sprint: 044 (UI Slot Consumer)
> Date: 2026-07-07
> Status: Local implementation complete; local verification passed.

## Scope

This manifest records local evidence for the UI facet consumer sprint:
`ui.research_workspace` contributes Research workspace panel metadata through
the Slot Platform, `/v1/ui-panels` exposes read-only panel rows behind
`DOGE_FEATURE_SLOT_PLATFORM` and `DOGE_FEATURE_SLOT_UI`, and
`ResearchAgentView.vue` renders existing panels through the frontend panel
registry.

## Implementation Evidence

| Area | Evidence |
|---|---|
| ADR | `docs/architecture/adr-0053-ui-slot-consumer.md` records the UI slot consumer decision. |
| CDD | `design/cdd/sprint-044-ui-slot-consumer.md` records behavior, contracts, and acceptance criteria. |
| Feature flag | `src/doge/config/settings.py` adds `DOGE_FEATURE_SLOT_UI` lifecycle metadata and `FeatureConfig.slot_ui`. |
| Capability discovery | `src/doge/application/capabilities/registry.py` exposes `feature.slot_ui`. |
| UI slot provider | `src/doge/platform/workspace/ui_slot.py` adds `ui.research_workspace`. |
| Backend registry | `src/doge/platform/workspace/ui_panels.py` adds `UIPanelRegistry`. |
| Slot factory | `src/doge/bootstrap/runtime_factories/slots.py` registers the UI slot and adds `build_slot_aware_ui_panels()` / `build_slot_ui_panel_rows()`. |
| API dependency | `src/doge/interfaces/api/deps.py` exposes UI panel rows through the API dependency layer. |
| API route | `src/doge/interfaces/gateway/routers/slots.py` adds `GET /v1/ui-panels`. |
| Gateway manifest | `src/doge/interfaces/gateway/slot.py` declares `/v1/ui-panels`. |
| Web panel registry | `web/src/views/panelRegistry.ts` defines Research workspace panel metadata and filters. |
| Web view consumer | `web/src/views/ResearchAgentView.vue` renders existing panels through `showPanel(panel_id)`. |
| Web store/API | `web/src/api/platform.ts` and `web/src/stores/platform.ts` add UI panel read plumbing. |
| Route authority | `docs/API.md`, `docs/reference/http-api.md`, `design/cdd/fastapi-service.md`, `docs/registry/entities.yaml`, and route governance tests now track 95 HTTP routes. |
| Unit tests | `tests/unit/platform/slots/test_builtin_ui_slot.py`, `tests/unit/platform/workspace/test_ui_panel_registry.py`, and Web `panelRegistry.spec.ts` cover UI slot and panel registry behavior. |
| Contract tests | `tests/contract/test_slot_ui_registry.py`, `tests/contract/test_slot_api.py`, and `tests/contract/test_gateway_slot_parity.py` cover UI panel consumer/API parity. |
| Runtime maturity | `docs/progress/runtime-maturity.yaml` adds the UI slot consumer evidence record. |
| Session state | `production/session-state/active.md` records Sprint 044 as the current local implementation. |

## Verification Commands

```bash
py -3 -m pytest tests/test_settings.py tests/unit/use_cases/test_capability_registry.py tests/unit/platform/slots/test_builtin_ui_slot.py tests/unit/platform/workspace/test_ui_panel_registry.py tests/contract/test_slot_ui_registry.py tests/contract/test_slot_api.py tests/contract/test_gateway_slot_parity.py tests/cli/test_cli_slots.py tests/cli/test_doged_cli.py -q
cd web && npm run test -- src/views/panelRegistry.spec.ts src/stores/platform.spec.ts src/views/ResearchAgentView.spec.ts
cd web && npm run test
py -3 -m pytest tests/contract/test_api_doc_route_coverage.py tests/unit/governance/test_s017_planning_docs.py -q
cd web && npm run build
py -3 -m pytest tests/unit/architecture/test_slot_boundary.py tests/unit/architecture/test_bootstrap_owns_factories.py -q
py -3 -m pytest tests/unit/platform/slots tests/unit/eval tests/unit/platform/workspace/test_ui_panel_registry.py tests/contract/test_tool_registry_slot_parity.py tests/contract/test_agent_backends_slot_parity.py tests/contract/test_workflow_slot_parity.py tests/contract/test_governance_slot_parity.py tests/contract/test_watcher_slot_parity.py tests/contract/test_document_slot_parity.py tests/contract/test_data_source_slot_parity.py tests/contract/test_gateway_slot_parity.py tests/contract/test_eval_slot_parity.py tests/contract/test_slot_kernel_bundle_rows.py tests/contract/test_slot_ui_registry.py tests/contract/test_slot_api.py tests/cli/test_cli_slots.py tests/cli/test_doged_cli.py -q
py -3 tools/ci/sdk-contract-check.py
py -3 scripts/validate_import_boundaries.py
py -3 scripts/validate_docs_authority.py
py -3 scripts/validate_docs_links.py
py -3 scripts/validate_docs_maturity_claims.py
py -3 scripts/validate_alpha_maturity_honesty.py --file docs/architecture/adr-0053-ui-slot-consumer.md
py -3 scripts/validate_alpha_maturity_honesty.py --file design/cdd/sprint-044-ui-slot-consumer.md
py -3 scripts/validate_adr_index_completeness.py
py -3 scripts/validate_governance_yaml_shape.py
py -3 scripts/validate_no_stale_counts.py
py -3 scripts/validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/openclaw-like-magical-barto.md
git diff --check
cmd.exe /c git diff --check
```

## Verification Results

| Gate | Result |
|---|---|
| UI slot/settings/API/CLI focused Python suite | Passed: 93 tests, 2 existing FastAPI deprecation warnings. |
| Focused Web panel/store/ResearchAgentView suite | Passed: 14 tests. |
| Full Web test suite | Passed: 163 tests. |
| API route coverage and governance route sync | Passed: 39 tests, 2 existing FastAPI deprecation warnings. |
| Web build | Passed. |
| Architecture boundary gates | Passed: 22 tests. |
| Slot consumer parity suite | Passed: 195 tests, 2 existing FastAPI deprecation warnings. |
| SDK contract | Passed: 15 surfaces, 15 entity parity checks. |
| Import boundaries | Passed. |
| Docs authority | Passed. |
| Docs links | Passed: 111 markdown files. |
| Docs maturity claims | Passed. |
| ADR/CDD maturity guard | Passed for ADR-0053 and Sprint 044 CDD. |
| ADR index / governance YAML | Passed. |
| Stale route/count guard | Passed. |
| Plan closure | Passed as acceptable-open: 2 gates passed, 4 external/operator gates still open. |
| Whitespace | Passed: WSL and Windows Git diff checks. |

## Posture

- Production posture unchanged: `production_ready: false`,
  `stable_declaration: forbidden`, `level_3_sdk_platform: experimental`.
- No external/operator gates are closed by this sprint.
- No Web Slot Center, dynamic component loading, SDK slot client, persistence
  schema, ModelRouter, ProfileRegistry, bundle activation, SlotLoader,
  third-party slot install, signing, runtime permission enforcement, active
  health probe, or enterprise allowlist is part of this sprint.
- Slot Platform remains experimental and feature-flagged off by default.
- Sprint 044 completes the UI facet consumer proof only; it does not complete
  the full OpenClaw-like Slot Platform.
