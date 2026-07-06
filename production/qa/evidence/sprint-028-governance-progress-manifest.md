# Sprint 028 - Governance Progress Manifest

> Sprint: 028 (Governance Progress)
> Date: 2026-07-05
> Status: Local implementation complete; final verification passed.

## Scope

This manifest records local evidence for case-level governance workflow
progress.

## Implementation Evidence

| Area | Evidence |
|---|---|
| ADR | `docs/architecture/adr-0037-case-progress-contract.md` records the case progress decision. |
| CDD | `design/cdd/sprint-028-governance-progress.md` records acceptance criteria. |
| Domain model | `src/doge/core/domain/platform_models.py` defines `CaseProgressStep`. |
| Persistence | `src/doge/infrastructure/database/agent_schema.sql` and `migration_runner.py` add `case_progress_steps`. |
| Repository | `src/doge/infrastructure/database/platform_repository.py` persists and lists progress steps. |
| Service | `src/doge/platform/workspace/application/case_service.py` builds persisted or derived case progress. |
| API response models | `src/doge/interfaces/gateway/routers/_response_models.py` defines `CaseProgressStepResponse` and `CaseProgressEnvelopeResponse`. |
| API route | `src/doge/interfaces/gateway/routers/cases.py` adds `GET /v1/research-cases/{case_id}/progress`. |
| Python SDK | `packages/doge-sdk-python/doge_sdk/platform.py` exposes sync and async `get_case_progress()`. |
| TypeScript SDK | `packages/doge-sdk-typescript/src/platform.ts` exposes `getCaseProgress()` and `platform-types.ts` exports `CaseProgressStep`. |
| Web API/store | `web/src/api/platform.ts` exposes `getCaseProgress()` and `web/src/stores/platform.ts` caches progress by case. |
| Web UI | `web/src/components/case/CaseProgressPanel.vue` renders progress in `CaseDetailView.vue`. |
| Route authority | `docs/reference/http-api.md`, `docs/API.md`, `docs/registry/entities.yaml`, and related governance docs agree on 90 HTTP routes. |
| Tests | `tests/unit/infrastructure/test_platform_repository.py`, `tests/contract/test_platform_api.py`, `tests/contract/test_python_sdk.py`, `packages/doge-sdk-typescript/src/__tests__/client.spec.ts`, `web/src/components/case/CaseProgressPanel.spec.ts`, and `web/src/stores/platform.spec.ts`. |

## Verification Commands

```bash
py -3 -m pytest tests/unit/infrastructure/test_platform_repository.py::test_platform_repository_persists_case_assets_executions_and_decisions tests/contract/test_platform_api.py::test_research_case_execution_preflight_and_execute_records_execution tests/contract/test_python_sdk.py::test_python_sdk_get_case_progress -q
cd packages/doge-sdk-typescript && npm test -- --run src/__tests__/client.spec.ts
cd web && npm test -- --run src/components/case/CaseProgressPanel.spec.ts src/stores/platform.spec.ts
py -3 tools/ci/sdk-contract-check.py
py -3 -m pytest tests/contract/test_api_doc_route_coverage.py tests/unit/governance/test_s017_planning_docs.py -q
py -3 scripts/validate_docs_authority.py
py -3 scripts/validate_docs_links.py
py -3 scripts/validate_import_boundaries.py
py -3 scripts/validate_docs_maturity_claims.py
py -3 scripts/validate_alpha_maturity_honesty.py --file docs/architecture/adr-0037-case-progress-contract.md
py -3 scripts/validate_alpha_maturity_honesty.py --file design/cdd/sprint-028-governance-progress.md
py -3 scripts/validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/agent-quizzical-wolf.md
git diff --check
```

## Verification Results

| Gate | Result |
|---|---|
| E4 focused repository/API/Python SDK tests | Passed: 3 tests. |
| TypeScript SDK client spec | Passed: 17 tests. |
| Web progress/store focused suite | Passed: 5 tests. |
| SDK contract | Passed: 15 surfaces, 15 entity parity checks. |
| API route coverage and governance route docs | Passed: 39 tests. |
| Docs authority | Passed. |
| Docs links | Passed: 95 markdown files validated. |
| Import boundaries | Passed. |
| Docs maturity claims | Passed. |
| ADR/CDD maturity guard | Passed for ADR-0037 and Sprint 028 CDD. |
| Plan closure | Passed with controlled open posture: 4 open / 2 passed. |
| Whitespace | Passed with WSL and Windows Git `diff --check`. |

## Posture

- Production posture unchanged.
- No external/operator gates are closed by this sprint.
- No SLA engine, notification automation, editable workflow step UI, or
  production-ready declaration is part of this sprint.
