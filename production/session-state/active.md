# Active Session State

> Living checkpoint. Gitignored. Read this first after any compaction/crash.
> Branch: `main` · Date: 2026-06-30

## Current Task

MY-DOGE-MICRO Sprint G architecture consolidation — **LOCAL IMPLEMENTATION COMPLETE / REMOTE CI PASSED / EXTERNAL GATES OPEN**. Legacy API and gateway router implementations are physically split behind compatibility shims, doctor commands are implemented for `doge` and `doged`, legacy documents registration now uses persisted document services, implicit user-facing `portfolio-demo` defaults were removed, and the agent tool registry was split into `doge.application.tools`. Sprint G adds shim/boundary guards, direct RuntimeKernel lifecycle integration, configurable scripted scenarios, eval/batch cleanup, worker metrics, streaming document upload, and refreshed boundary docs. Sprint G closure SHA `ee4c3283bb69ae21671ffd2d9fef908e4819ce16` has exact-SHA GitHub Actions CI run `28448012096` with result `success`; latest remotely verified SHA now points to that SHA with evidence at `production/qa/evidence/ci/remote-ci-ee4c328.json`. W3-live, S017-003, AUTH-prod, and S017-007 remain external/operator gated.

## Phase Status

- **Runtime Consolidation Local Remediation (2026-06-30)**: **LOCAL CODE COMPLETE / EXTERNAL GATES OPEN**
  - Interface split: legacy router implementations live under `doge.interfaces.api_legacy.routers`; `/v1` gateway router implementations live under `doge.interfaces.gateway.routers`; old `doge.interfaces.api.routers` paths remain re-export shims.
  - Diagnostics: `doge doctor [--json]` checks local config, database paths, tracked views SQL, agent DB access, document storage writability, and model provider configuration; `doged doctor [--json] [--port]` reports `/health/ready` readiness checks.
  - Documents: legacy `POST /api/documents` now goes through `FileUploadService` and the persisted repository path instead of an in-memory `_DOCUMENTS` registry.
  - Portfolio defaults: run/turn/API/CLI/use-case defaults now mean no portfolio unless `portfolio_id` is explicitly supplied; `portfolio-demo` remains limited to seed/demo/test evidence.
  - Scripted model default: offline `ScriptedAgentModel` now skips portfolio exposure unless the runtime context carries an explicit authorized portfolio id.
  - Tools: canonical tool-registry imports now come from `doge.application.tools`; `doge.application.agent.tools` remains a compatibility shim.
  - Governance: `docs/architecture/module-boundaries.md` and `docs/progress/runtime-maturity.yaml` record local structure convergence while preserving `production_ready: false`, `stable_declaration: forbidden`, and Level 3 experimental posture.
  - Closure gate posture: unchanged controlled-open posture with `S017-003`, `W3-live`, `AUTH-prod`, and `S017-007` still open.

- **Sprint G (Architecture Consolidation)**: **LOCAL IMPLEMENTATION COMPLETE / EXTERNAL GATES OPEN**
  - Plan: `C:\Users\WSMAN\.claude\plans\according-to-a-document-fluttering-raven.md`
  - QA plan: `production/qa/qa-plan-sprint-g.md`
  - Evidence: `production/qa/evidence/sprint-g-architecture-consolidation.md`
  - Sprint G closure CI: `ee4c328` exact-SHA run `28448012096` completed with conclusion `success`.
  - Latest remotely verified SHA: `ee4c328` with CI run `28448012096`.
  - Local additions: API v1 shim parity/boundary guards, direct runtime lifecycle integration tests, configurable scripted scenario fixtures, source eval runner, CLI batch command, worker metrics, streaming document upload, file structure policy, and Sprint G evidence.
  - Maturity posture: `production_ready: false`, `stable_declaration: forbidden`, Level 3 `experimental`.

- **Sprint F (Evaluation Quality Closure)**: **LOCAL ENGINEERING COMPLETE / EXTERNAL GATES OPEN**
  - Gate: deterministic local retrieval/citation baseline through persisted runtime
  - CDD: `design/cdd/sprint-f-evaluation-quality-closure.md`
  - Sprint plan: `production/sprints/sprint-f-evaluation-quality-closure.md`
  - QA plan: `production/qa/qa-plan-sprint-f.md`
  - Runtime benchmark: `tests/eval/test_gold_set_runtime.py`
  - CLI: `scripts/run_citation_quality_benchmark.py`
  - Baseline evidence:
    - `production/qa/evidence/eval/citation-quality-baseline-2026-06-29.json`
    - `production/qa/evidence/eval/citation-quality-baseline-2026-06-29.md`
    - `production/qa/evidence/eval/citation-quality-trend-history-2026-06-29.jsonl`
  - Metrics: 35/35 observations, retrieval recall 1.0, retrieval precision 1.0, citation precision 1.0, claim/evidence precision 1.0, support accuracy 1.0, numerical consistency 1.0, usage coverage 1.0.
  - SF-007 fix: explicit tool-result `evidence_id` values are preserved, explicit empty evidence results no longer create fallback citation chunks, and doubled `evd-evd-*` markers are blocked.
  - SF-008 trend history: local trend-history append/validate CLI exists; repeat append of the same baseline reports `changed: false`.
  - W3-live posture: local baseline includes `w3_live_observation_input` and `w3_live_closure_allowed: false`; W3-live remains open until real analyst/operator evidence exists.
  - Closure gate posture: `scripts/validate_plan_closure_gate.py --allow-open` now reports 4 open / 2 passed (`S017-002`, `S017-006` passed).

- **Sprint E (Adaptive Milner Bounded-Context Convergence)**: **COMPLETE / GO_LOCAL**
  - Gate: Eight bounded-context convergence under ADR-0021, ADR-0022, and ADR-0024
  - CDD: `design/cdd/sprint-e-adaptive-milner-convergence.md` (Accepted)
  - QA plan: `production/qa/qa-plan-sprint-e.md`
  - Review log: `design/cdd/reviews/sprint-e-adaptive-milner-convergence-review-log.md`
  - Acceptance report: `production/qa/evidence/sprint-e-adaptive-milner-convergence-acceptance-2026-06-29.md`
  - Local focused gates: **PASSED**
  - Web tests/build: **PASSED**
  - Runtime maturity: Sprint E recorded as passed without maturity promotion
  - Full Python regression: **1817 passed, 3 failed, 8 skipped**
  - The 3 full-regression failures were reproduced in a clean detached `87572a0` worktree and are not Sprint E regressions.

- **Sprint D (Enterprise Auth Hardening)**: **COMPLETE / TOOLING COMPLETE / GO_LOCAL / PENDING_LIVE**
  - Story: S017-004 / AUTH-prod
  - Gate: Enterprise auth boundary (AUTH-001 through AUTH-008)
  - Local implementation: **COMPLETE**
    - CDD created: `design/cdd/sprint-d-enterprise-auth-hardening.md` (promoted to Accepted)
    - Runtime maturity updated: `docs/progress/runtime-maturity.yaml`
    - Smoke evidence: 4 doged enterprise auth scripts + SDK external consumer smoke
    - Production validation template: `enterprise-production-validation-template-2026-06-22.json`
    - Acceptance report: `production/qa/evidence/sprint-d-enterprise-auth-hardening-acceptance-2026-06-29.md`
  - Local smoke evidence: **ALL PASSED**
    - Static bearer: `production/qa/evidence/manual/doged-enterprise-static-auth-smoke-2026-06-22.json`
    - JWKS: `production/qa/evidence/manual/doged-enterprise-jwks-auth-smoke-2026-06-22.json`
    - Process secret: `production/qa/evidence/manual/doged-enterprise-process-secret-auth-smoke-2026-06-22.json`
    - Remote bind gate: `production/qa/evidence/manual/doged-remote-bind-gate-smoke-2026-06-22.json`
  - Test Review: APPROVED (85 focused tests passed)
  - Runtime/Gate Review: APPROVED
  - Internal external-gate tooling: **COMPLETE**
    - Unified IdP/JWKS operator tool: `scripts/doge_idp_jwks_operator_tool.py`
    - Enterprise production evidence builder/validator/templates: complete
    - External gate preflight/handoff tooling: complete
  - Overall Strict Live Verdict: **GO_LOCAL / PENDING_LIVE**

- **Sprint C (Kimi Live Smoke Closure)**: **COMPLETE / GO**
  - Story: S017-002
  - Gate: Kimi Coding v1 (required text + Vision; optional Files + Agent SDK)
  - Acceptance report: `production/qa/evidence/sprint-c-kimi-live-smoke-acceptance-2026-06-29.md`
  - Sprint status: S017-002 now `done` in `production/sprint-status.yaml`.

- **Sprint B (Citation/Evidence Closure)**: **COMPLETE / ACCEPTED**
  - Base committed SHA: `fd1768fa690a9a0c3a8d7905a7b72f0af54f6b04`
  - Acceptance report: `production/qa/evidence/sprint-b-citation-evidence-acceptance-2026-06-28.md`

- **P0-P2 (local-refactor phases)**: COMPLETE
- **P3 (external gates)**: internal tooling complete. Strict live/operator evidence still open for S017-003, W3-live, AUTH-prod, and S017-007.

## Sprint D Local Changes

1. Created Sprint D CDD: `design/cdd/sprint-d-enterprise-auth-hardening.md` with all 8 product sections (status promoted to Accepted).
2. Updated `docs/progress/runtime-maturity.yaml` with `sprint_d_enterprise_auth_hardening` gate tracking.
3. Refreshed all 4 enterprise auth smoke scripts with passing evidence (files retain 2026-06-22 name; contents refreshed 2026-06-29):
   - Static bearer auth smoke
   - JWKS auth smoke
   - Process secret auth smoke
   - Remote bind gate smoke
4. SDK external consumer smoke passed.
5. Created Sprint D QA plan: `production/qa/qa-plan-sprint-d.md`.
6. Production validation evidence template, builder, and validator exist with passing tests.
7. Unified IdP/JWKS operator tool added for `jwks-inspect`, `env-template`, `make-invalid-signature`, `run-smoke`, and `build-evidence`.
8. 147 enterprise-focused tests passed; full regression 1784 passed, 2 pre-existing failures, 8 skipped.

## Latest Verification

- Runtime consolidation CLI suite: **23 passed, 2 warnings**
- Sprint G closure exact-SHA CI: **passed**, GitHub Actions run `28448012096` for `ee4c3283bb69ae21671ffd2d9fef908e4819ce16`; latest remotely verified SHA now records `ee4c328`
- Sprint G final local verification: architecture guard suite **109 passed, 2 warnings**; eval suite **13 passed, 2 warnings**; CLI/worker/upload suite **34 passed, 2 warnings**
- Sprint G CLI batch smoke: **10/10 cases passed** with `tests\eval\cases_expanded.json`
- Sprint G focused suites: WP1/WP3/WP4/WP5 **21 passed**; WP6 **13 passed**; WP7 **20 passed**; WP2 **42 passed**
- Sprint G validators: docs links **62 markdown files validated**; alpha maturity honesty **passed**; plan closure gate **acceptable open**, 4 open / 2 passed; strict plan closure gate **failed as expected** while external gates remain open; `git diff --check` **passed**
- Scripted portfolio default focused suite: **34 passed, 67 warnings** (`test_scripted_agent_model.py`, `test_context_builder.py`, `test_runtime_kernel.py`)
- 2026-06-30 Gate Pack: **prepared/validated**, `production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-30/`; external-input preflight remains pending as intended
- Runtime consolidation contract/API suite: **24 passed, 2 warnings**
- Layer/governance focused suite: **75 passed, 3 warnings**
- Tool/portfolio focused suite: **38 passed**
- Web targeted Research Agent store/view suite: **2 files passed, 4 tests passed**
- Plan closure gate: **acceptable open**, 4 open / 2 passed (`S017-002`, `S017-006` passed; `S017-003`, `W3-live`, `AUTH-prod`, `S017-007` open)
- Alpha fast pre-commit readiness: **passed** with `--mode fast --skip-pending-scope`
- Sprint F runtime benchmark: **2 passed**
- Citation-quality CLI: **passed**, generated `citation-quality-baseline-2026-06-29.json` and `.md`
- Citation-quality metrics after SF-007: **citation_precision 1.0**
- Trend-history CLI: **passed**, generated and validated `citation-quality-trend-history-2026-06-29.jsonl`; repeat append returned `changed: false`
- Sprint F eval suite: **12 passed**
- Sprint F agent/QA targeted suite: **43 passed**
- Governance/QA unit suite: **348 passed**
- Agent unit suite: **233 passed, 83 warnings**
- Citation integration suite: **4 passed, 7 warnings**
- Kimi Coding v1 evidence: **passed** with `--coding-v1` and without `--allow-blocked`
- Plan closure gate: **acceptable open**, 4 open / 2 passed
- Kimi/glowing completion audit validators: **passed**
- Plan closure manifest/runbook validators: **passed**
- Alpha fast pre-commit readiness: **passed**
- Sprint E focused Python gates: **62 passed**
- API/Python SDK contracts: **34 passed, 2 FastAPI deprecation warnings**
- README/governance docs gates: **25 passed**
- Web tests: **15 files passed, 92 tests passed**
- Web build: **passed**
- Docs validators: `validate_docs_links.py` validated 61 markdown files; `generate_docs_status.py --check` up to date.
- Full Python regression: **1817 passed, 3 failed, 8 skipped, 124 warnings**
- New failures introduced by Sprint E: **0**
- Pre-existing/baseline failures reproduced at clean `87572a0`: 3
  - `tests/test_transport.py::TestStdioTransport::test_stdio_initialize` — stdio initialize response absent.
  - `tests/test_yfinance_adapter.py::test_download_kline_normalizes_columns_and_dtypes` — yfinance StringDtype drift.
  - `tests/unit/qa/test_validate_alpha_pre_commit_readiness.py::test_alpha_pre_commit_readiness_cli_fast` — Windows GBK decode path in alpha readiness validator subprocess output handling.
- CRLF classifier: `git diff --ignore-cr-at-eol --shortstat` reports tracked content changes as `41 files changed, 791 insertions(+), 272 deletions(-)`.

## Posture (unchanged)

- production_ready: false; stable_declaration: forbidden; Level 3 experimental.
- External gate tooling: complete under the internal runner/builder/validator/template completion posture.
- Strict live/operator gates open: S017-003, W3-live, AUTH-prod (local/tooling complete, live pending), S017-007.

## Open External Gates (Sprint D)

- **live_idp_jwks**: Live IdP/JWKS smoke against operator-approved identity provider
- **production_secret_store**: Live KMS/Vault/cloud command smoke, permissions, rotation
- **siem_worm_export**: Production SIEM/WORM sink integration and operator sign-off
- **live_remote_bind**: Live remote-bind deployment smoke in operator-approved environment
- **production_data_isolation_review**: Cross-table tenant partition audit with staging/production snapshot
- **sdk_registry_release**: SDK registry publication, release-manager approval, registry-backed consumer smoke (S017-007)

## Commits this session

No commit was requested for the current Runtime Consolidation remediation. Current changes remain in the working tree.

## Do Not Forget

- Remaining P3 external gates still require operator action; do NOT fabricate live evidence.
- Do not change production_ready / stable_declaration / Level 3 posture.
- ADR-0015 remains Proposed until all live evidence lands.
- Next recommended work: operator-owned W3-live/S017-003/AUTH-prod/S017-007 external gates, when real credentials, approvals, and analyst evidence are available.

## Files Modified (git working tree)

- Runtime consolidation current themes:
  - `src/doge/interfaces/api_legacy/routers/*`, `src/doge/interfaces/gateway/routers/*`, and compatibility shims under `src/doge/interfaces/api/routers/*`
  - `src/doge/interfaces/cli/commands/doctor.py`, `src/doge/interfaces/cli/main.py`, and `src/doge/interfaces/daemon/main.py`
  - `src/doge/application/tools/*` and `src/doge/application/agent/tools.py` shim
  - portfolio default cleanup across run/turn/use-case/unit-of-work/API/CLI paths
  - persisted legacy document route wiring
  - focused tests and governance docs for the local structure convergence

- `tests/eval/gold_set_seed.py` (new)
- `tests/eval/gold_set_runner.py` (new)
- `tests/eval/test_gold_set_runtime.py` (new)
- `scripts/run_citation_quality_benchmark.py` (new)
- `scripts/analyst_trend_history.py` (local baseline append/validate CLI)
- `src/doge/platform/runtime/services.py` (explicit evidence ID preservation and empty-result fallback guard)
- `src/doge/application/agent/artifact_citation_assembler.py` (non-duplicating citation marker format)
- `production/qa/evidence/eval/citation-quality-baseline-2026-06-29.json` (generated)
- `production/qa/evidence/eval/citation-quality-baseline-2026-06-29.md` (generated)
- `production/qa/evidence/eval/citation-quality-trend-history-2026-06-29.jsonl` (generated)
- `design/cdd/sprint-f-evaluation-quality-closure.md` (new)
- `production/sprints/sprint-f-evaluation-quality-closure.md` (new)
- `production/qa/qa-plan-sprint-f.md` (new)
- `production/sprint-status.yaml` (Sprint F + S017-002 reconciliation)
- `docs/progress/runtime-maturity.yaml` (Sprint F local benchmark gate)
- `production/session-state/active.md` (updated)
- `scripts/validate_plan_closure_gate.py` (Coding v1 S017-002 gate alignment)
- `docs/progress/9b77f9c-external-closure-runbook.md` and completion audits (4 open / 2 passed gate posture)
- `tests/unit/agent/test_tool_execution_service.py`, `tests/unit/agent/test_artifact_citation_assembler.py`, and `tests/unit/qa/test_analyst_trend_history.py` (SF-007/SF-008 regression coverage)
