# Sprint 028 CDD: Governance Progress

Status: Ready for Acceptance
Date: 2026-07-05

## User Promise

An analyst can open a research case and see where the governance workflow stands
across intake, evidence readiness, workflow execution, and decision without
opening each related asset, run, or review panel.

## Delivered Contract

Sprint 028 implements E4 from
`C:\Users\WSMAN\.claude\plans\agent-quizzical-wolf.md`:

- `CaseProgressStep` records `status`, `owner`, `timestamp`,
  `blocking_issue`, and `next_action`.
- `case_progress_steps` persists explicit case progress with tenant scoping and
  one row per `(case_id, step_key)`.
- `GET /v1/research-cases/{case_id}/progress` returns persisted steps when
  present and derived case progress otherwise.
- Python SDK exposes `client.platform.get_case_progress(case_id)`.
- TypeScript SDK exposes `client.platform.getCaseProgress(caseId)` and exports
  `CaseProgressStep`.
- Web exposes `getCaseProgress(caseId)` through the shared SDK client.
- Platform store caches progress in `caseProgressByCaseId`.
- `CaseProgressPanel.vue` renders progress in `CaseDetailView.vue`.
- API route authority, entity registry, route coverage tests, SDK contract, and
  governance docs are synchronized at 90 HTTP routes.

## Non-Goals

- No editable workflow step UI.
- No SLA engine, notification policy, or escalation automation.
- No semantic memo diff.
- No external/operator gate closure.
- Current maturity posture remains `production_ready: false`,
  `stable_declaration: forbidden`, and Level 3 `experimental`.

## Acceptance Criteria

- Repository persists a progress step and reads it back by case.
- API returns `{"case_id": ..., "source": ..., "steps": [...]}` for progress.
- Derived progress contains the standard `intake`, `evidence`, `workflow`, and
  `decision` steps.
- Progress step fields include `status`, `owner`, `timestamp`,
  `blocking_issue`, and `next_action`.
- Python SDK maps to `/v1/research-cases/{case_id}/progress`.
- TypeScript SDK maps to `/v1/research-cases/{case_id}/progress`.
- Web store loads progress with `loadCaseWorkspace()`.
- Case detail renders progress with status labels and blocking context.
- SDK contract check includes the new route and response type.
- API docs and route registries include the case progress route.

## Validation Plan

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

## Local Verification Result

Final local verification passed. Focused repository/API/Python SDK tests,
TypeScript SDK tests/build, Web progress/store tests/build, SDK contract parity,
API route coverage, governance docs, docs authority/links/maturity validators,
import boundaries, plan closure, and whitespace checks all passed.

## Out of Scope

- B6 run comparison, completed by Sprint 027.
- External production/provider/operator gates.
