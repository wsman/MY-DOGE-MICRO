# Active Session State

> Living checkpoint. Tracked in Git until a separate governance decision changes retention. Read this first after any compaction/crash.
> Branch: `main` · Date: 2026-07-05

## Current Task

**Sprint 023 (Structured Claims Contract) — LOCAL IMPLEMENTATION COMPLETE / READY FOR LOCAL ACCEPTANCE.** Plan: B3 Phase 1 from `C:\Users\WSMAN\.claude\plans\agent-quizzical-wolf.md`. Sprint 023 closes the contract-foundation part of B3 by adding additive structured claim metadata for research memo conclusions: `claim_id`, `claim_text`, `status`, `evidence_refs`, `numeric_check_status`, and `risk_level`. Delivered scope: shared structured-claims builder; citation assembler writes `AgentArtifact.data.structured_claims`; run summary use case projects the same fields into `/v1/runs/{run_id}/claims`; `RunClaimResponse` and TypeScript SDK `RunClaim` parity updated; Web ResearchAgentView reads a compact structured-claims fixture; ADR-0030, CDD, sprint record, and evidence manifest added. Full conclusion-evidence matrix UI remains deferred. Maturity posture unchanged; external/operator gates S017-003 / W3-live / AUTH-prod / S017-007 remain open. Manifest: `production/qa/evidence/sprint-023-structured-claims-contract-manifest.md`. Sprint record: `production/sprints/sprint-023-structured-claims-contract.md`.

Predecessor — **Sprint 022 (Approval Explanation Metadata) — LOCAL IMPLEMENTATION COMPLETE / READY FOR LOCAL ACCEPTANCE / COMMITTED `bfa960e`.** Plan: `C:\Users\WSMAN\.claude\plans\agent-quizzical-wolf.md`. Sprint 022 closes UX-2 deferred item B4 with an additive `AgentApproval` metadata extension: `why_needed`, `impact`, `deny_consequence`, and `publish_target`. Delivered scope: domain fields and keyword-only `AgentRun.add_approval` metadata; run-stepper propagation into approval objects and `APPROVAL_REQUESTED` events; governance provider explanation text; fresh SQLite schema and idempotent legacy migration; repository and runtime-transaction persistence; `/v1/runs/{run_id}/approvals` `ApprovalResponse`/`ApprovalListResponse`; TypeScript SDK optional fields and 13-entry SDK parity; Python/TypeScript SDK README notes; Web approval detail rows; runtime golden contract, focused tests, ADR-0029, CDD, sprint record, and evidence manifest. Maturity posture unchanged; approval resolution and entitlement behavior unchanged; external/operator gates S017-003 / W3-live / AUTH-prod / S017-007 remain open. Manifest: `production/qa/evidence/sprint-022-approval-explanation-manifest.md`. Sprint record: `production/sprints/sprint-022-approval-explanation.md`.

Predecessor — **UX-2 (Scenario Completion & Run-Readiness) — LOCAL IMPLEMENTATION COMPLETE / READY FOR LOCAL ACCEPTANCE.** Plan: `C:\Users\WSMAN\.claude\plans\agent-quizzical-wolf.md`. UX-2 closes the genuine local remainder from the repeated strategic review after UX-1: README now starts with `doge start`; Web ScenarioPicker live-browses workflow templates while preserving a feature-flag-safe fallback; built-in workflow templates add `risk_alert` and `portfolio_impact_note`; ResearchAgentView shows a RunPreflightChecklist before Run; and `doge brief` prints a six-section CN market brief without changing the file-writing market overview path. Maturity posture unchanged; no `/v1` or SDK public-surface change; external/operator gates S017-003 / W3-live / AUTH-prod / S017-007 remain open. Manifest: `production/qa/evidence/sprint-ux-2-review-reconciliation-manifest.md`. Sprint record: `production/sprints/sprint-ux-2-scenario-completion-and-run-readiness.md`.

Predecessor — **UX-1 (First-Run Coherence & Honest Maturity Disclosure) — LOCAL IMPLEMENTATION COMPLETE / READY FOR LOCAL ACCEPTANCE.** Plan: `C:\Users\WSMAN\.claude\plans\agent-sharded-lagoon.md`. UX-1 completes the first-run Local Alpha product path without changing production posture: `doge start` 5-path launcher, `doge doctor --next`, CLI REPL `/status` + grouped `/help`, shared run-status labels, Web MaturityPanel / ScenarioPicker / EmptyStateCtas / GuidedFlow, and ADR-0028 workflow-slug threading through `/v1/sessions/{session_id}/turns`, SDKs, worker, run use case, and Web store. Acceptance residue was closed on 2026-07-05: Web launcher/docs now open Vite at `127.0.0.1:5173` (daemon/API remains `8901`), `validate_plan_closure_gate.py` supports `--source-plan` while preserving the old default, the UX-1 CDD is `Ready for Acceptance`, and ADR-0028 validation criteria are checked after verification. Maturity posture unchanged; external gates S017-003 / W3-live / AUTH-prod / S017-007 remain open/operator-owned. Sprint record: `production/sprints/sprint-ux-1-first-run-coherence.md`.

Predecessor — **Sprint 021 (Narrative Reconciliation & Docs Hygiene) — LOCAL IMPLEMENTATION COMPLETE (Slices 0–5).** Plan: `C:\Users\WSMAN\.claude\plans\web-demo-concurrent-cray.md`. A re-pasted strategic review's conclusions were accurate ("architecture-complete Local Alpha, not production ready"); three exploration passes verified all 8 architecture claims TRUE and sorted the review's "P0" list into already-shipped local evidence, operator/external-gated (S017-003 / W3-live / AUTH-prod / S017-007), and one ADR-conflict (the rejected "5 platform modules" lens vs ADR-0021). This docs-only sprint closed the genuine narrative remainder: reconciled the three scenario enumerations onto an explicit value/delivery two-axis framing (`docs/product/user-scenarios.md`, `docs/architecture/module-boundaries.md`); added a README "Architecture At A Glance" block (counts only; rejects the 5-platform-module lens); added the coordinated maturity vocabulary (Local Alpha / Production-shaped / Production-readiness gates open / not production ready) to README and `docs/scenarios/demo-scenarios.md`; refined the `run_stream.py` module docstring (behavior unchanged). Maturity posture unchanged; external gates remain operator-owned. Manifest: `production/qa/evidence/sprint-021-narrative-reconciliation-manifest.md`. Sprint record: `production/sprints/sprint-021-narrative-reconciliation-and-docs-hygiene.md`.

Predecessor — **Sprint 020 (Strategic-Review Reconciliation & Genuinely-Remaining Closure) — LOCAL IMPLEMENTATION COMPLETE (Slices 0–5).** Plan: `C:\Users\WSMAN\.claude\plans\my-doge-micro-glistening-dawn.md`. A re-pasted strategic review proposed a broad structural refactor; AST/file-verified exploration confirmed ~90% already shipped (14 STALE / 2 DONE / 8 PARTIAL of 24 claims — manifest at `production/qa/evidence/sprint-020-review-reconciliation-manifest.md`). This sprint closed the genuine remainder: unified the MCP server's six data tools onto the shared `ToolRegistry` (`doge.application.tools`) and removed the parallel `doge.interfaces.mcp.tools` wrapper package (new convergence contract test + architecture gate); added `doged serve --host`; added `docs/scenarios/demo-scenarios.md`; restored the README Surface Classification table; deleted an orphaned pyc and corrected the stale tool-shim note at `:58`. Maturity posture unchanged; external gates S017-003 / W3-live / AUTH-prod / S017-007 remain operator-owned. Sprint record: `production/sprints/sprint-020-strategic-review-reconciliation-and-remainder-closure.md`.

Predecessor — **Sprint 019 (Platform Facade Adoption & Boundary Consolidation) — LOCAL IMPLEMENTATION COMPLETE (Slices 0–5).** Plan: `C:\Users\WSMAN\.claude\plans\kimi-majestic-clarke.md`. The pasted strategic review's "next step" (product README + platform facades + SDK/Web contract) was already shipped (Sprints E/G/H/I/018); this sprint closed the genuine remainder. Outcomes: migrated 16 of 18 `doge.application.*` interface imports to `doge.platform.*`/`doge.products.portfolio` facades (2 grandfathered: `session_use_cases`, `GenerateMacroReportRequest`); extended `platform.evidence` (`FileUploadTooLargeError`) and `platform.runtime` (`OutboxPublisher`) re-exports; reconciled the duplicate `doge.application.runtime` facade to ADR-0027 deprecation; added a facade-adoption ratchet gate (`test_interface_layers_use_platform_facades`, 2-entry frozen allowlist, negative-probed); closed P2/P3 boundary gaps (gateway↔adapters location rule in `validate_import_boundaries.py`, platform/*→products rule + relative-import resolution, 7 dead `module-ownership.yaml` paths removed with a stale-entry guard, `tests/unit/architecture` in the `ci-runtime-gateway` job); removed unused `module_eval`/`module_platform` markers. Maturity posture unchanged; external gates S017-003 / W3-live / AUTH-prod / S017-007 remain operator-owned. Final full regression: 1776 passed, 8 skipped. Sprint record: `production/sprints/sprint-019-platform-facade-adoption-and-boundary-consolidation.md`.

Predecessor — **Sprint 018 (Product Surface & SDK Contract Convergence) — LOCAL IMPLEMENTATION COMPLETE (Slices 0–4).** Plan: `C:\Users\WSMAN\.claude\plans\validated-tumbling-rabbit.md` (审查修订版). Outcomes: TS SDK is the single platform-entity type source (`packages/doge-sdk-typescript/src/platform-types.ts`); Web no longer maintains `web/src/types/platform.ts` (10 consumers import from `doge-sdk`); 12 platform entity response schemas are now in OpenAPI via `response_model` (`src/doge/interfaces/gateway/routers/_response_models.py`, `extra="allow"` preserves the wire); `tools/ci/sdk-contract-check.py` enforces OpenAPI↔TS property parity (caught + fixed a real RunEval drift — TS extended to the full 16-field shape); four `src/doge/products/*/README.md`; Web primary nav aligned to the four product modules (Market/Research/Portfolio/Quant, D1) with no GovernanceDomainView product module (D2). Deferred follow-ups: response_model for CaseReview/HomeQueue/full AgentRun aggregates; dataclass↔Pydantic response-model sync guardrail. Maturity posture unchanged; external gates S017-003 / W3-live / AUTH-prod / S017-007 remain operator-owned (S017-002 / S017-006 passed).

Predecessor — MY-DOGE-MICRO remaining local quality-gate remediation — **SPRINT I LOCAL IMPLEMENTATION COMPLETE / LEVEL 1 CLI ALPHA / LEVEL 2 ALPHA / LEVEL 3 EXPERIMENTAL / EXTERNAL GATES BLOCKED ON OPERATOR INPUT**. Sprint H compatibility-surface governance is locally committed as `a8c832f` and is not remotely verified. The local quality-gate remediation baseline freezes runtime contracts, locks ToolDescriptor-backed metadata, adds a deterministic RAG retrieval benchmark/evidence, compresses README/API primary path guidance, and records external-gate preflight blockers without closing any external gate. Sprint I adds API semantic compression, SDK README alignment, and focused full-app `/v1` smoke coverage without changing wire contracts or maturity posture. Sprint G remote CI evidence remains the latest remotely verified SHA at `ee4c3283bb69ae21671ffd2d9fef908e4819ce16`. W3-live, S017-003, AUTH-prod, and S017-007 remain external/operator gated.

## Phase Status

- **Sprint 023 (Structured Claims Contract)**: **LOCAL IMPLEMENTATION COMPLETE / READY FOR LOCAL ACCEPTANCE / EXTERNAL GATES UNCHANGED**
  - Plan: B3 Phase 1 from `C:\Users\WSMAN\.claude\plans\agent-quizzical-wolf.md`
  - ADR: `docs/architecture/adr-0030-structured-claim-contract.md` (Accepted)
  - CDD: `design/cdd/sprint-023-structured-claims-contract.md` (`Ready for Acceptance`)
  - Manifest: `production/qa/evidence/sprint-023-structured-claims-contract-manifest.md`
  - Sprint record: `production/sprints/sprint-023-structured-claims-contract.md`
  - Delivered: `structured_claims` artifact data; run summary claim projection with `status`, `evidence_refs`, `numeric_check_status`, and `risk_level`; TypeScript SDK parity; compact Web structured-claims read path.
  - Still deferred: full conclusion-evidence matrix UI and external/operator gates.
  - Verification: focused structured-claims suite 37 passed; `sdk-contract-check` passed (13 surfaces, 13 entity parity); Web `ResearchAgentView.spec.ts` passed.

- **Sprint 022 (Approval Explanation Metadata)**: **LOCAL IMPLEMENTATION COMPLETE / READY FOR LOCAL ACCEPTANCE / EXTERNAL GATES UNCHANGED**
  - Plan: `C:\Users\WSMAN\.claude\plans\agent-quizzical-wolf.md`
  - ADR: `docs/architecture/adr-0029-additive-approval-explanation-fields.md` (Accepted)
  - CDD: `design/cdd/sprint-022-approval-explanation.md` (`Ready for Acceptance`)
  - Manifest: `production/qa/evidence/sprint-022-approval-explanation-manifest.md`
  - Sprint record: `production/sprints/sprint-022-approval-explanation.md`
  - Delivered: additive `AgentApproval` explanation metadata (`why_needed`, `impact`, `deny_consequence`, `publish_target`); run-stepper/provider propagation; SQLite schema/migration/repository persistence; `/v1` `ApprovalResponse` and `ApprovalListResponse`; TypeScript SDK optional fields and SDK parity entry; Web approval detail rows; golden runtime fixture and focused tests.
  - Maturity posture unchanged; approval resolution and entitlement behavior unchanged; external/operator gates S017-003 / W3-live / AUTH-prod / S017-007 remain open. Sprint not registered in `production/sprint-status.yaml` (UX/product-acceptance record, no new story-status tracking needed).
  - Verification: focused Python/API/runtime suite 62 passed; governance/tool provider regression 34 passed; `sdk-contract-check` passed (13 surfaces, 13 entity parity); Web `ResearchAgentView.spec.ts` passed; Web build passed; docs authority / docs maturity claims / alpha maturity honesty / docs links / import boundaries passed; plan closure with `--source-plan C:/Users/WSMAN/.claude/plans/agent-quizzical-wolf.md` remained open 4 / passed 2 / failed 0 / invalid 0.

- **UX-2 (Scenario Completion & Run-Readiness)**: **LOCAL IMPLEMENTATION COMPLETE / READY FOR LOCAL ACCEPTANCE / EXTERNAL GATES UNCHANGED**
  - Plan: `C:\Users\WSMAN\.claude\plans\agent-quizzical-wolf.md`
  - CDD: `design/cdd/sprint-ux-2-scenario-completion-and-run-readiness.md` (`Ready for Acceptance`)
  - Manifest: `production/qa/evidence/sprint-ux-2-review-reconciliation-manifest.md`
  - Sprint record: `production/sprints/sprint-ux-2-scenario-completion-and-run-readiness.md`
  - Delivered: README first-run `doge start` pointer; ScenarioPicker live-browse with four-template fallback; `risk_alert` and `portfolio_impact_note` built-in workflow templates; RunPreflightChecklist in ResearchAgentView; `doge brief` CN console market brief; CLI docs/tests synchronization.
  - Maturity posture unchanged; no `/v1` wire-contract change; no SDK public-surface change; external/operator gates S017-003 / W3-live / AUTH-prod / S017-007 remain open. Sprint not registered in `production/sprint-status.yaml` (UX/product-acceptance record, no new story-status tracking needed).
  - Verification: Python focused UX-2 suite 34 passed; Web focused UX-2 suite 9 passed; Web build passed; docs authority / docs maturity claims / alpha maturity honesty / docs links / import boundaries / SDK contract passed; plan closure with `--source-plan C:/Users/WSMAN/.claude/plans/agent-quizzical-wolf.md` remained open 4 / passed 2 / failed 0 / invalid 0.

- **UX-1 (First-Run Coherence & Honest Maturity Disclosure)**: **LOCAL IMPLEMENTATION COMPLETE / READY FOR LOCAL ACCEPTANCE / EXTERNAL GATES UNCHANGED**
  - Plan: `C:\Users\WSMAN\.claude\plans\agent-sharded-lagoon.md`
  - CDD: `design/cdd/sprint-ux-1-first-run-coherence.md` (`Ready for Acceptance`)
  - ADR: `docs/architecture/adr-0028-additive-session-turn-workflow-field.md` (Accepted; validation criteria checked 2026-07-05)
  - Sprint record: `production/sprints/sprint-ux-1-first-run-coherence.md`
  - Delivered: `doge start` first-run launcher; `doge doctor --next`; CLI REPL `/status` + grouped `/help`; shared run-status labels across CLI/Web; Web MaturityPanel, ScenarioPicker, EmptyStateCtas, and GuidedFlow; workflow slug threading through daemon turn path, SDKs, worker/use case, and Web.
  - Acceptance-residue fixes: Web workspace guidance now opens Vite at `http://127.0.0.1:5173` while `8901` remains daemon/API; `validate_plan_closure_gate.py --source-plan` targets `agent-sharded-lagoon.md` without breaking the legacy default source plan; CDD placeholders removed; ADR-0028 checklist updated after verification.
  - Maturity posture unchanged; external gates S017-003 / W3-live / AUTH-prod / S017-007 remain open. Sprint not registered in `production/sprint-status.yaml` (completed governance/product-acceptance record, no new story-status tracking needed).
  - Verification: Python focused UX-1 suite 29 passed / 2 warnings; Web tests 110 passed; Web build passed; docs links 86 files; docs maturity claims / docs authority / alpha maturity honesty / import boundaries passed; sdk-contract-check passed (13 surfaces, 12 entity parity); plan closure with `--source-plan C:/Users/WSMAN/.claude/plans/agent-sharded-lagoon.md` remained open 4 / passed 2 / failed 0 / invalid 0; `git diff --check` and Windows Git diff check clean.

- **Sprint 021 (Narrative Reconciliation & Docs Hygiene)**: **LOCAL IMPLEMENTATION COMPLETE / EXTERNAL GATES UNCHANGED**
  - Plan: `C:\Users\WSMAN\.claude\plans\web-demo-concurrent-cray.md`
  - Manifest: `production/qa/evidence/sprint-021-narrative-reconciliation-manifest.md`
  - Sprint record: `production/sprints/sprint-021-narrative-reconciliation-and-docs-hygiene.md`
  - Documentation/text-only. Reconciled the three scenario enumerations onto a value/delivery two-axis framing (`docs/product/user-scenarios.md`, `docs/architecture/module-boundaries.md`); added README "Architecture At A Glance" (counts only; rejects the "5 platform modules" lens vs ADR-0021); added coordinated maturity vocabulary to README + `docs/scenarios/demo-scenarios.md`; refined `run_stream.py` module docstring (behavior unchanged).
  - Maturity posture unchanged; external gates S017-003 / W3-live / AUTH-prod / S017-007 remain open. Sprint not registered in `production/sprint-status.yaml` (Sprint 020 precedent for docs-only sprints).
  - Verification: docs_authority / docs_maturity_claims / alpha_maturity_honesty / no_stale_counts / generate_docs_status --check all passed; docs_links 85 files; test_docs_consistency 7 passed; streaming + run_stream_handler 17 passed; architecture + governance + layer_gates 190 passed / 3 skipped; plan closure `--allow-open` 4 open / 2 passed / 0 invalid; `git diff --check` clean. Full regression 1785 passed / 8 skipped / 1 pre-existing failure (real-HTTP `test_cli_gateway_approval_resume_smoke_over_real_v1_http`; reproduced identically on clean `a2f616b` after stashing all working-tree changes — not caused by this docs-only sprint nor by the in-progress `sqlite.py`).

- **Sprint 020 (Strategic-Review Reconciliation & Genuinely-Remaining Closure)**: **LOCAL IMPLEMENTATION COMPLETE / EXTERNAL GATES UNCHANGED**
  - Plan: `C:\Users\WSMAN\.claude\plans\my-doge-micro-glistening-dawn.md`
  - Manifest: `production/qa/evidence/sprint-020-review-reconciliation-manifest.md`
  - Sprint record: `production/sprints/sprint-020-strategic-review-reconciliation-and-remainder-closure.md`
  - MCP six data tools converged onto the shared `ToolRegistry`; removed `doge.interfaces.mcp.tools` wrapper package (new convergence contract + architecture gate).
  - Added `doged serve --host`; added `docs/scenarios/demo-scenarios.md`; restored README Surface Classification table; housekeeping (orphaned pyc, `active.md:58` note).
  - Maturity posture unchanged; external gates S017-003 / W3-live / AUTH-prod / S017-007 remain open.
  - Verification: focused gate suite 430 passed / 4 skipped; MCP suite 86 passed; boundary / SDK-contract (13 surfaces, 12 parity) / alpha / docs-links (85 files) all passed; plan closure `--allow-open` 4 open / 2 passed / 0 invalid; `git diff --check` clean. Three full-suite failures (legacy-API + two SSE) pass in isolation — flaky/pre-existing, unrelated to Sprint 020 surfaces.

- **Sprint 019 (Platform Facade Adoption & Boundary Consolidation)**: **LOCAL IMPLEMENTATION COMPLETE / EXTERNAL GATES UNCHANGED**
  - Plan: `C:\Users\WSMAN\.claude\plans\kimi-majestic-clarke.md`
  - Manifest: `production/qa/evidence/sprint-019-facade-adoption-manifest.md`
  - Sprint record: `production/sprints/sprint-019-platform-facade-adoption-and-boundary-consolidation.md`
  - Migrated 16 of 18 `doge.application.*` interface imports to `doge.platform.*`/`doge.products.portfolio` facades; 2 grandfathered (`session_use_cases`, `GenerateMacroReportRequest`).
  - Extended `platform.evidence` (`FileUploadTooLargeError`) and `platform.runtime` (`OutboxPublisher`); reconciled `doge.application.runtime` to ADR-0027 deprecation.
  - New facade-adoption ratchet gate (`test_interface_layers_use_platform_facades`, 2-entry frozen allowlist); closed P2/P3 boundary gaps (gateway↔adapters location rule, platform/*→products + relative resolution, 7 dead ownership paths removed with stale-entry guard, architecture tests in `ci-runtime-gateway`); removed unused `module_eval`/`module_platform` markers.
  - Maturity posture unchanged; external gates S017-003 / W3-live / AUTH-prod / S017-007 remain open.
  - Verification: focused suites 333 passed / 4 skipped; boundary validator, SDK contract (13 surfaces, 12 parity), alpha maturity honesty all passed; plan closure `--allow-open` 4 open / 2 passed / 0 invalid; `git diff --check` clean. Final full regression 1776 passed / 8 skipped.

- **Sprint I (API Semantic Compression)**: **LOCAL IMPLEMENTATION COMPLETE / EXTERNAL GATES UNCHANGED**
  - Plan: `C:\Users\WSMAN\.claude\plans\bubbly-inventing-llama.md`
  - QA plan: `production/qa/qa-plan-sprint-i.md`
  - Evidence: `production/qa/evidence/sprint-i-api-doc-compression.md`
  - `docs/API.md` now centers the main API narrative on five primary `/v1` families: `sessions`, `runs`, `documents`, `tools`, and `platform`.
  - `health`, `portfolios`, `audit`, and `enterprise` are documented as operator/reference APIs, not primary user-path resources.
  - Added Python and TypeScript SDK READMEs documenting current resources: `sessions`, `runs`, `documents`, `platform`, and `capabilities`.
  - `/v1/tools` is documented and tested as API discovery; no first-class SDK `tools` resource was added.
  - Added full-app contract smoke coverage for `/v1/tools`, `/v1/capabilities`, and platform feature-flag-disabled behavior.
  - Maturity posture: `production_ready: false`, `stable_declaration: forbidden`, Level 1/2 Alpha, Level 3 `experimental` — unchanged.
  - External gates: S017-003, W3-live, AUTH-prod, S017-007 remain open.
  - Focused verification: v1/platform/API-doc route suite **38 passed, 2 warnings**; Python SDK suite **23 passed**; docs links **65 markdown files validated** after evidence/session-state updates; alpha maturity honesty **passed**; governance YAML shape **passed**, 5 files checked / 0 findings; plan closure gate **acceptable open**, 4 open / 2 passed; strict plan closure gate **failed as expected**; `git diff --check` **passed**.

- **Sprint H (Compatibility Surface 减法)**: **LOCAL IMPLEMENTATION COMPLETE / EXTERNAL GATES UNCHANGED**
  - Plan: `C:\Users\WSMAN\.claude\plans\bubbly-inventing-llama.md`
  - QA plan: `production/qa/qa-plan-sprint-h.md`
  - Evidence: `production/qa/evidence/sprint-h-compatibility-surface-governance.md`
  - Created `docs/architecture/compatibility-surfaces.md` with registry entries for compatibility, legacy, and demo/test surfaces.
  - Added `tests/unit/architecture/test_shim_behavior_guards.py` with AST-based checks enforcing ADR-0027 rules across shim files.
  - Added `tests/unit/architecture/test_composition_allowlist.py` freezing the current public callable surface in `doge.application.composition`, including `refresh_views`.
  - Updated `README.md` with Canonical/Compatibility/Legacy/Demo-Test path classification table; aligned Level 1 maturity from Preview to Alpha.
  - Maturity posture: `production_ready: false`, `stable_declaration: forbidden`, Level 3 `experimental` — unchanged.
  - External gates: S017-003, W3-live, AUTH-prod, S017-007 remain open.
  - Sprint H validators: docs links validated 64 markdown files; alpha maturity honesty passed; governance YAML shape passed; plan closure gate `--allow-open` acceptable with 4 open / 2 passed; strict closure gate failed as expected; `git diff --check` passed.
  - Architecture test suite: 122 passed, 2 warnings.

- **Runtime Consolidation Local Remediation (2026-06-30)**: **LOCAL CODE COMPLETE / EXTERNAL GATES OPEN**
  - Interface split: legacy router implementations live under `doge.interfaces.api_legacy.routers`; `/v1` gateway router implementations live under `doge.interfaces.gateway.routers`; old `doge.interfaces.api.routers` paths remain re-export shims.
  - Diagnostics: `doge doctor [--json]` checks local config, database paths, tracked views SQL, agent DB access, document storage writability, and model provider configuration; `doged doctor [--json] [--port]` reports `/health/ready` readiness checks.
  - Documents: legacy `POST /api/documents` now goes through `FileUploadService` and the persisted repository path instead of an in-memory `_DOCUMENTS` registry.
  - Portfolio defaults: run/turn/API/CLI/use-case defaults now mean no portfolio unless `portfolio_id` is explicitly supplied; `portfolio-demo` remains limited to seed/demo/test evidence.
  - Scripted model default: offline `ScriptedAgentModel` now skips portfolio exposure unless the runtime context carries an explicit authorized portfolio id.
  - Tools: canonical tool-registry imports come from `doge.application.tools`; the legacy `doge.application.agent.tools` shim was removed in Sprint M (see `docs/progress/runtime-maturity.yaml`).
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

- UX-2 focused Python suite: **34 passed** (`tests\cli\test_cli_brief.py`, `tests\unit\workspace_workflow\test_template_seed.py`, `tests\test_market_reporting.py`, `tests\cli\test_cli_arg_parsing.py`)
- UX-2 focused Web suite: **9 passed** (`npm run test -- src/components/agent/ScenarioPicker.spec.ts src/components/agent/RunPreflightChecklist.spec.ts src/views/ResearchAgentView.spec.ts`); Web build **passed** (`npm run build`)
- UX-2 docs/governance: docs authority **passed**; docs maturity claims **passed**; alpha maturity honesty **passed**; docs links **86 markdown files validated**; import boundaries **passed**; SDK contract **passed** (13 surfaces, 12 entity parity)
- UX-2 CLI smoke: template seed dry-run listed 10 built-ins; `doge brief --market cn` printed all six sections with local no-data placeholders; `doge brief --market us` exited non-zero with the expected unavailable-data message
- UX-2 plan closure: `validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/agent-quizzical-wolf.md` **acceptable open**, 4 open / 2 passed / 0 failed / 0 invalid; `production_ready: false` and `stable_declaration: forbidden` unchanged

- UX-1 focused Python suite: **29 passed, 2 warnings** (`tests/cli/test_cli_start.py`, `tests/unit/qa/test_validate_plan_closure_gate.py`, `tests/contract/test_session_turn_workflow.py`, `tests/unit/architecture/test_no_hardcoded_workflow_in_agent_store.py`, `tests/unit/architecture/test_no_raw_run_status_in_web.py`, `tests/unit/interfaces/test_run_status_labels.py`)
- UX-1 Web regression: **110 passed** (`npm run test`); Web build **passed** (`npm run build`)
- UX-1 docs/governance: `validate_alpha_maturity_honesty.py --file C:/Users/WSMAN/.claude/plans/agent-sharded-lagoon.md` **passed**; `validate_docs_links.py` **86 markdown files validated**; `validate_docs_maturity_claims.py` **passed**; `validate_docs_authority.py` **passed**
- UX-1 contract/boundary: `validate_import_boundaries.py` **passed**; `tools/ci/sdk-contract-check.py` **passed** (13 surfaces, 12 entity parity); `git diff --check` and Windows Git `diff --check` **passed**
- UX-1 plan closure: `validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/agent-sharded-lagoon.md` **acceptable open**, 4 open / 2 passed / 0 failed / 0 invalid; `production_ready: false` and `stable_declaration: forbidden` unchanged

- Runtime/tool contract focused suite: **7 passed, 2 warnings** (`tests\contract\test_golden_runtime_contract.py`, `tests\contract\test_tool_registry.py`)
- RAG retrieval focused suite: **2 passed** (`tests\eval\test_rag_retrieval_benchmark.py`, `tests\integration\test_rag_retrieval.py`)
- Architecture guard suite: **122 passed, 2 warnings** (`tests\unit\architecture`)
- Eval/RAG suite: **24 passed, 2 warnings** (`tests\integration\test_rag_retrieval.py`, `tests\eval`)
- Docs links: **65 markdown files validated**
- Alpha maturity honesty: **passed**
- Governance YAML shape: **passed**, 5 files checked / 0 findings
- Plan closure gate `--allow-open`: **acceptable open**, 4 open / 2 passed
- Strict plan closure gate: **failed as expected**, 4 open / 2 passed while external gates remain open
- `git diff --check`: **passed**
- RAG retrieval baseline CLI: **passed**, generated `production\qa\evidence\eval\rag-retrieval-quality-baseline-2026-07-01.json` and `.md` with retrieval recall@k 1.0, chunk precision 1.0, citation linkage 1.0, numerical consistency 1.0, and `external_gate_closure_allowed=false`
- External closure preflight for `S017-003`, `W3-live`, `AUTH-prod`, and `S017-007`: **failed as expected with infrastructure ready and external inputs blocked**; evidence note at `production/qa/evidence/plan-closure/external-preflight-blocked-2026-07-01.md`
- Sprint H shim behavior guards: **9 passed** (`tests\unit\architecture\test_shim_behavior_guards.py`)
- Sprint H composition allowlist: **4 passed** (`tests\unit\architecture\test_composition_allowlist.py`)
- Sprint H architecture suite: **122 passed, 2 warnings** (`tests\unit\architecture`)
- Sprint H docs/governance validators: docs links **64 markdown files validated**; alpha maturity honesty **passed**; governance YAML shape **passed**, 5 files checked / 0 findings; plan closure gate **acceptable open**, 4 open / 2 passed; strict plan closure gate **failed as expected** while external gates remain open; `git diff --check` **passed**
- Alpha local Level 1 hardening (2026-06-30): **2 passed** (`tests\unit\agent\test_model_response_assembler.py`, `tests\eval\test_multi_turn_citation_context.py`)
- CLI session focused suite: **15 passed**
- Python SDK contract suite: **23 passed**
- Real loopback gateway approval smoke: **1 passed**, with uvicorn/TestClient-style local daemon startup warnings only
- TypeScript SDK suite: **16 passed**
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

Sprint H compatibility-surface governance was locally committed as `a8c832f` (`docs(architecture): govern compatibility surfaces`) and is not remotely verified yet. The local quality-gate remediation baseline is included in the latest local commit and is not remotely verified.

## Do Not Forget

- Remaining P3 external gates still require operator action; do NOT fabricate live evidence.
- Do not change production_ready / stable_declaration / Level 3 posture.
- ADR-0015 remains Proposed until all live evidence lands.
- Next recommended work: operator-owned W3-live/S017-003/AUTH-prod/S017-007 external gates, when real credentials, approvals, and analyst evidence are available.

## Latest Local Commit Scope

- Local quality-gate remediation:
  - `docs/architecture/runtime-contracts.md`
  - `tests/fixtures/runtime_contracts/agent_runtime_contract_v1.json`
  - `tests/contract/test_golden_runtime_contract.py`
  - `tests/contract/test_tool_registry.py`
  - `src/doge/application/tools/registry.py`
  - `tests/eval/rag_retrieval_benchmark.py`
  - `tests/eval/test_rag_retrieval_benchmark.py`
  - `scripts/run_rag_quality_benchmark.py`
  - `production/qa/evidence/eval/rag-retrieval-quality-baseline-2026-07-01.json`
  - `production/qa/evidence/eval/rag-retrieval-quality-baseline-2026-07-01.md`
  - `production/qa/evidence/plan-closure/external-preflight-blocked-2026-07-01.md`
  - `README.md`
  - `docs/progress/runtime-maturity.yaml`
  - `production/session-state/active.md`
  - `docs/API.md`
