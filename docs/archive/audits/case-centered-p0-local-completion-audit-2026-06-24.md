# Case-Centered P0 Local Completion Audit - 2026-06-24

## Verdict

The case-centered P0 implementation is locally complete and verified.

The only remaining Definition-of-Done gate is remote exact-SHA CI evidence for
the implementation commit. The current worktree is uncommitted, so it must not
be described as remotely verified.

## Scope

Source plan:

- `C:\Users\Aby\.claude\plans\main-quizzical-quilt.md`

Baseline:

- `main` HEAD before this work: `932338e`
- Current worktree: uncommitted implementation changes
- Remote CI evidence available before this work: `0058c5c` only

## Requirement Matrix

| Requirement | Local Evidence | Status |
|---|---|---|
| Research Case is the primary execution workspace | `web/src/views/CaseDetailView.vue`, `web/src/components/case/*`, `web/src/stores/platform.ts`, `production/qa/evidence/manual/case-workspace-browser-smoke-2026-06-23.json` | Proven locally |
| User can execute a template without typing a Run ID | `TemplateConfigurator.vue`, `CaseDetailView.vue`, `tests/contract/test_platform_api.py`, browser smoke confirms no primary manual Run ID copy | Proven locally |
| `POST /v1/research-cases/{case_id}/executions` preflights, creates run, queues it, records `WorkflowExecution`, returns `execution_id` and `run_id` | `src/doge/platform/workspace/service.py`, `src/doge/interfaces/api/routers/v1/platform.py`, `tests/contract/test_platform_api.py::test_research_case_execution_preflight_and_execute_records_execution` | Proven locally |
| Reopening a case restores assets, executions, latest review resources, and decisions | `ResearchCaseService.build_case_review`, `web/src/stores/platform.ts`, `web/src/stores/platform.spec.ts` | Proven locally |
| Web case workspace shows Memo/artifact, Claims, Citations, Eval, Approval, and Decision | `CaseDetailView.vue`, `CaseApprovalPanel.vue`, `CaseDecisionPanel.vue`, `case-workspace-ax-tree-2026-06-24.json` with `approval_region: true` | Proven locally |
| Home shows actionable queue items instead of static module-count cards | `web/src/views/HomeDashboardView.vue`, `ResearchCaseService.build_home_queue`, `tests/contract/test_platform_api.py::test_home_queue_returns_actionable_case_items`, `case-workspace-browser-smoke-2026-06-23.json` | Proven locally |
| Same template execution path is available from Web, CLI, Python SDK, TypeScript SDK, and MCP | Web `CaseDetailView.vue`; CLI `src/doge/interfaces/cli/commands/case.py`; SDK clients; MCP tools; `tests/cli/test_cli_platform_workflow.py`, `tests/contract/test_python_sdk.py`, `packages/doge-sdk-typescript/src/__tests__/client.spec.ts`, `tests/test_mcp_tools.py::TestPlatformWorkflowTools` | Proven locally |
| Old `/research-agent` remains functional | `web/src/router/index.ts`, `platform-shell-default-entry-smoke-2026-06-24.json`, `case-workspace-browser-smoke-2026-06-23.json` | Proven locally |
| Old run-link API and existing SDK methods remain functional | `POST /v1/research-cases/{case_id}/runs` remains implemented; `tests/contract/test_platform_api.py`, `tests/contract/test_python_sdk.py`, TypeScript SDK tests | Proven locally |
| No production-ready/stable/GA/beta/hosted-enterprise or remotely verified latest-HEAD claim | Plan status, defaultization audit, and this audit keep `production_ready: false`, `stable_declaration: forbidden`, and remote CI pending | Proven locally |
| Platform Shell default entry | `web/src/config/features.ts`, `web/src/router/index.ts`, `web/src/router/productNavigation.spec.ts`, `platform-shell-default-entry-smoke-2026-06-24.json` | Proven locally |
| Platform Shell rollback | `VITE_DOGE_FEATURE_PLATFORM_SHELL=0` route guard, `platform-shell-default-entry-smoke-2026-06-24.json`, `docs/archive/audits/platform-shell-defaultization-2026-06-24.md` | Proven locally |
| Case Workspace accessibility preflight | `scripts/case_workspace_ax_tree_smoke.py`, `production/qa/evidence/manual/case-workspace-ax-tree-2026-06-24.json`, `case-workspace-ax-tree-2026-06-24.md` | Proven locally as browser AX-tree preflight; not a human screen-reader pass |
| Backend feature defaults remain controlled | `docs/archive/audits/feature-flag-deprecation-plan-2026-06-23.md`, `docs/archive/audits/platform-shell-defaultization-2026-06-24.md`, backend settings unchanged | Proven locally |
| Exact-SHA remote CI evidence for implementation SHA | Requires commit/push and CI run evidence | Pending external step |

## Verification Run

Observed local verification:

```text
Python full regression: 1359 passed, 9 skipped, 11 warnings
Web full tests: 15 files, 91 tests passed
Web production build: passed
TypeScript SDK: 1 file, 14 tests passed; build passed
Python SDK: sdist and wheel build passed
Platform/API/CLI/MCP targeted checks: passed
Browser default-entry smoke: passed
Case Workspace AX-tree smoke: passed
git diff --check: no whitespace errors
```

Browser evidence:

- `production/qa/evidence/manual/case-workspace-browser-smoke-2026-06-23.json`
- `production/qa/evidence/manual/case-workspace-ax-tree-2026-06-24.json`
- `production/qa/evidence/manual/platform-shell-default-entry-smoke-2026-06-24.json`

Defaultization audit:

- `docs/archive/audits/platform-shell-defaultization-2026-06-24.md`

## Remaining Gate

Remote exact-SHA CI is still pending because the implementation has not been
committed and pushed.

Required next evidence after commit/push:

```text
production/qa/evidence/ci/remote-ci-<implementation-sha>.json
docs/progress/remote-ci-evidence-<implementation-sha>.md
```

Until that evidence exists, the latest implementation must be described only as
locally verified.

## Non-Production Boundary

This audit does not claim:

- production readiness;
- stable runtime/API status;
- enterprise Beta, GA, hosted enterprise readiness, or external validation;
- closure of live Kimi, financial-provider approval, analyst benchmark,
  enterprise-production, or SDK-registry gates.
