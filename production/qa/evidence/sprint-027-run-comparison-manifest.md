# Sprint 027 - Run Comparison Manifest

> Sprint: 027 (Run Comparison)
> Date: 2026-07-05
> Status: Local implementation complete; final verification passed.

## Scope

This manifest records local evidence for compact persisted run history and Web
run comparison.

## Implementation Evidence

| Area | Evidence |
|---|---|
| ADR | `docs/architecture/adr-0036-run-list-and-comparison.md` records the compact list decision. |
| CDD | `design/cdd/sprint-027-run-comparison.md` records acceptance criteria. |
| API response models | `src/doge/interfaces/gateway/routers/_response_models.py` defines `RunListItemResponse` and `RunListResponse`. |
| API route | `src/doge/interfaces/gateway/routers/run_queries.py` adds `GET /v1/runs`. |
| Python SDK | `packages/doge-sdk-python/doge_sdk/run.py` exposes sync and async `runs.list()`. |
| TypeScript SDK | `packages/doge-sdk-typescript/src/run.ts` exposes `RunListItem` and `runs.list()`. |
| Web API | `web/src/api/agent.ts` exposes `listAgentRuns()`. |
| Web UI | `web/src/components/agent/RunComparisonPanel.vue` renders recent rows in `ResearchAgentView.vue`. |
| Route authority | `docs/reference/http-api.md`, `docs/API.md`, `docs/registry/entities.yaml`, and related governance docs include the compact run-list route. |
| Tests | `tests/contract/test_v1_api.py`, `tests/contract/test_python_sdk.py`, `packages/doge-sdk-typescript/src/__tests__/client.spec.ts`, `web/src/components/agent/RunComparisonPanel.spec.ts`, and `web/src/views/ResearchAgentView.spec.ts`. |

## Verification Commands

```bash
py -3 -m pytest tests/contract/test_v1_api.py::test_v1_list_runs_returns_compact_comparison_rows tests/contract/test_python_sdk.py::test_python_sdk_list_runs -q
cd packages/doge-sdk-typescript && npm test -- --run src/__tests__/client.spec.ts
cd web && npm test -- --run src/components/agent/RunComparisonPanel.spec.ts src/views/ResearchAgentView.spec.ts
py -3 tools/ci/sdk-contract-check.py
py -3 -m pytest tests/contract/test_api_doc_route_coverage.py tests/unit/governance/test_s017_planning_docs.py -q
py -3 scripts/validate_docs_authority.py
py -3 scripts/validate_docs_links.py
py -3 scripts/validate_import_boundaries.py
py -3 scripts/validate_docs_maturity_claims.py
py -3 scripts/validate_alpha_maturity_honesty.py --file docs/architecture/adr-0036-run-list-and-comparison.md
py -3 scripts/validate_alpha_maturity_honesty.py --file design/cdd/sprint-027-run-comparison.md
py -3 scripts/validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/agent-quizzical-wolf.md
git diff --check
```

## Verification Results

| Gate | Result |
|---|---|
| B6 focused Python route/SDK tests | Passed: 2 tests. |
| TypeScript SDK client spec | Passed: 17 tests. |
| Web comparison/view focused suite | Passed: 6 tests. |
| SDK contract | Passed: 15 surfaces, 15 entity parity checks after Sprint 028. |
| API route coverage and governance route docs | Passed: 39 tests at 90 HTTP routes after Sprint 028. |
| Docs authority | Passed. |
| Docs links | Passed: 95 markdown files validated. |
| Import boundaries | Passed. |
| Docs maturity claims | Passed. |
| ADR/CDD maturity guard | Passed for ADR-0036 and Sprint 027 CDD. |
| Plan closure | Passed with controlled open posture: 4 open / 2 passed. |
| Whitespace | Passed with WSL and Windows Git `diff --check`. |

## Posture

- Production posture unchanged.
- No external/operator gates are closed by this sprint.
- No full memo diff, persistence schema migration, research-case timeline, or
  new run status enum value is part of this sprint.
