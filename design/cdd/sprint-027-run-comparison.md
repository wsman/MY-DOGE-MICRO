# Sprint 027 CDD: Run Comparison

Status: Ready for Acceptance
Date: 2026-07-05

## User Promise

An analyst can see recent persisted runs next to the current Research Agent
workspace and compare basic status, workflow, and evidence volume without
opening every run individually.

## Delivered Contract

Sprint 027 implements B6 from
`C:\Users\WSMAN\.claude\plans\agent-quizzical-wolf.md`:

- `GET /v1/runs` lists compact persisted runs.
- Python SDK exposes `client.runs.list(limit=20, session_id=None)`.
- TypeScript SDK exposes `client.runs.list({ limit, sessionId })`.
- Web exposes `listAgentRuns(limit)` through the shared SDK client.
- `RunComparisonPanel.vue` renders recent run rows in the Research Agent quality
  pane and highlights the current run.
- API route authority, entity registry, route coverage tests, SDK contract, and
  SDK README docs are synchronized.

## Non-Goals

- No full memo semantic diff.
- No new run status enum values.
- No persistence schema migration.
- No research-case timeline.
- No pagination cursor contract beyond `limit`.
- No external/operator gate closure.
- Current maturity posture remains `production_ready: false`,
  `stable_declaration: forbidden`, and Level 3 `experimental`.

## Acceptance Criteria

- `/v1/runs` returns `{"runs": [...]}` with compact rows and no full `events` or
  `artifacts` arrays.
- The route supports `limit` and optional `session_id`.
- Python SDK list helper maps to `/v1/runs`.
- TypeScript SDK list helper maps to `/v1/runs` and exports `RunListItem`.
- Web comparison panel renders recent rows, status labels, evidence counts, and
  current-run highlighting.
- ResearchAgentView tests still mount with API mocks.
- SDK contract check includes the new route and response type.
- API docs and route registries include the compact run-list route.

## Validation Plan

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

## Local Verification Result

Final local verification passed. Focused Python route/SDK tests, TypeScript SDK
tests/build, Web comparison/view tests/build, SDK contract parity, API route
coverage, governance docs, docs authority/links/maturity validators, import
boundaries, plan closure, and whitespace checks all passed.

## Out of Scope

- Governance workflow progress visualization.
- External production/provider/operator gates.
