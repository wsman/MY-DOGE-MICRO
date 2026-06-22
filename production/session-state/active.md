# Active Session State

> Living checkpoint. Gitignored. Read this first after any compaction/crash.
> Branch: `main` · Date: 2026-06-22

## Current Task

Implement and govern the platformization plan from
`C:\Users\Aby\.claude\plans\glowing-weaving-kettle.md`.

The user approved all file writes and subagent parallel work for this task.

## Baseline Truth

- Sprint 017 external validation is not fully closed.
- Current closure-gate posture remains **5 open / 1 passed**:
  - Passed: `S017-006` screen-reader manual evidence.
  - Open: `S017-002`, `S017-003`, `W3-live`, `AUTH-prod`, `S017-007`.
- Runtime maturity remains:
  - `production_ready: false`
  - `stable_declaration: forbidden`
  - Level 3 SDK/platform posture: experimental.
- Track A external evidence closure must not be diluted by Track B
  platformization work.

## Completed In This Session

- Rewrote `C:\Users\Aby\.claude\plans\glowing-weaving-kettle.md` into a
  two-track external-closure plus platformization plan.
- Added Phase 0 platform CDDs and Proposed ADRs:
  - `design/cdd/run-summary-citation-api.md`
  - `design/cdd/workspace-project-research-case.md`
  - `design/cdd/workflow-templates.md`
  - `design/cdd/platform-shell-ui.md`
  - `design/cdd/capability-registry.md`
  - `docs/architecture/adr-0016-user-level-objects.md`
  - `docs/architecture/adr-0017-run-summary-citation-api.md`
  - `docs/architecture/adr-0018-workflow-template-system.md`
  - `docs/architecture/adr-0019-capability-registry.md`
  - `docs/architecture/adr-0020-platform-shell-ui.md`
- Updated governance:
  - `docs/architecture/tr-registry.yaml`: TR-059 through TR-070.
  - `docs/registry/architecture.yaml`: systems #16-#20 and related stances.
  - `design/cdd/module-index.md`: 20-module platformization index.
  - `docs/progress/kimi-plan-completion-audit.md`: platformization addendum.
- Implemented feature-flagged backend slices:
  - `DOGE_FEATURE_RUN_SUMMARY_API`
  - `DOGE_FEATURE_PLATFORM_OBJECTS`
  - `DOGE_FEATURE_WORKFLOW_TEMPLATES`
  - `DOGE_FEATURE_CAPABILITY_REGISTRY`
- Added `/v1/runs/{run_id}/summary`, `/claims`, `/citations`, `/eval`.
- Added `/v1/workspaces`, `/v1/projects`, `/v1/research-cases`,
  `/v1/workflow-templates`, `/v1/capabilities`, and case-run linking.
- Added template-to-run creation through `/v1/research-cases/{case_id}/runs`
  with `template_id`, deterministic template policy merge into `ModelPolicy`,
  `run_created` template metadata, and additive `workflow_template_runs`
  association rows.
- Added capability provider split and tool capability discovery sourced from
  `ToolRegistry` metadata.
- Added Phase 5 provider-backed `ToolApplicationService` execution facade for
  market, portfolio, research, fundamental, quant, compliance, and publishing
  tool groups behind `DOGE_FEATURE_CAPABILITY_REGISTRY`; default direct
  execution remains the rollback path.
- Added platform SQLite tables, domain models, repository port/adapter,
  composition/dependency wiring, API docs, and contract/unit tests.
- Added Python SDK sync/async helpers for run summary, platform objects,
  workflow templates, and capability registry.
- Added TypeScript SDK source helpers and tests for the same surface.
- Added frontend platform data layer:
  - `web/src/types/platform.ts`
  - `web/src/api/platform.ts`
  - `web/src/stores/platform.ts`
  - `web/src/stores/platform.spec.ts`
- Added feature-flagged web platform shell:
  - `VITE_DOGE_FEATURE_PLATFORM_SHELL=1`
  - views for workspace list/detail, project detail, case detail, template
    center, run detail, and admin/capability registry.
  - `/research-agent` remains the default route when the shell flag is off.
- Verified Phase 4 using temporary local Node/npm and Chromium:
  - TypeScript SDK tests/build/pack dry-run.
  - Web full Vitest, default build, and platform-shell flag-on build.
  - Browser CDP smoke evidence at
    `production/qa/evidence/manual/platform-shell-browser-smoke-2026-06-22.json`.

## Verification Snapshot

- Governance YAML shape: PASS, 5 files, 0 findings.
- Plan closure gate with controlled opens:
  - `scripts/validate_plan_closure_gate.py --allow-open`
  - PASS result: `open`, summary 5 open / 1 passed.
- Python SDK and route coverage:
  - `.\.venv\Scripts\python.exe -m pytest tests\contract\test_python_sdk.py tests\contract\test_api_doc_route_coverage.py -q`
  - PASS: `22 passed`.
- Backend platform/run-summary targeted checks:
  - v1/run-summary/platform contracts plus SDK/route coverage: PASS, `32 passed`.
  - workflow-template/runtime/platform repository and run-summary/capability
    unit checks: PASS, `24 passed`.
  - Phase 5 capability provider/tool facade parity: PASS, `36 passed`.
  - agent runtime and enterprise ACL regression: PASS, `33 passed`.
  - broader targeted platform/capability/API set: PASS, `79 passed`.
  - governance/QA set: PASS, `44 passed`.
- TypeScript SDK:
  - `npm test`: PASS, `13 passed`.
  - `npm run build`: PASS.
  - `npm pack --dry-run --json`: PASS, 11 package entries.
- Web:
  - `npm test`: PASS, `81 passed`.
  - `npm run build`: PASS.
  - `VITE_DOGE_FEATURE_PLATFORM_SHELL=1 npm run build`: PASS.
- Flags-off/backend compatibility:
  - PASS, `57 passed`.
- Layer gates:
  - PASS, `65 passed, 1 warning`.
- Full Python unit regression:
  - PASS, `737 passed, 2 skipped, 8 warnings`.
- Contract/integration regression:
  - PASS, `115 passed, 1 skipped`.
- Eval regression:
  - PASS, `7 passed`.
- External closure manifest, handoff, and runbook validators:
  - PASS; external-input preflight reports infrastructure ready but pending
    operator inputs.
- Dedicated plan audit:
  - PASS; `docs/progress/glowing-weaving-kettle-completion-audit.md` is
    checked by `scripts/validate_glowing_weaving_kettle_completion_audit.py`.
  - Sprint 017 external-closure QA plan added:
    `production/qa/qa-plan-sprint-017.md`.
  - Governance/closure focused regression: PASS, `78 passed`.
- External closure handoff hardening:
  - `scripts/prepare_plan_closure_handoff.py --date 2026-06-22` now emits
    six per-gate `operator-input-guide.md` files.
  - Existing draft inputs are preserved with source/draft SHA-256 metadata:
    `preserved_existing_template_draft` means the draft still matches its
    template, while `preserved_existing_operator_draft` means it differs from
    the template. Generation no longer overwrites an already-filled draft input.
  - Handoff validator and unit tests reject missing/weak guide files, stale
    draft hashes, and action labels that do not match file hashes.
- Platform shell browser smoke:
  - PASS, `#/workspaces`, Workspaces view content, platform nav, Agent entry.
- `git diff --check`: PASS, LF/CRLF warnings only.
- Temporary Node/npm path used:
  `C:\Users\Aby\AppData\Local\Temp\codex-node-v24.17.0\node-v24.17.0-win-x64`.

## Next Useful Work

1. Re-run the closure/governance validators after the final doc updates.
2. Keep Track A external gates open until real passed/approved evidence exists.

## Do Not Forget

- Do not mark ADR-0016 through ADR-0020 Accepted without review evidence.
- Do not claim stable or production-ready runtime status.
- Do not mutate existing runtime/evidence tables with nullable platform context
  columns unless a follow-up ADR supersedes ADR-0016.
- Preserve `/research-agent` route compatibility when working on the shell.
