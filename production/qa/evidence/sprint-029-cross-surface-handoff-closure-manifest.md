# Sprint 029 - Cross-Surface Handoff Closure Manifest

> Sprint: 029 (Cross-Surface Handoff Closure)
> Date: 2026-07-06
> Status: Local implementation complete; final verification passed.

## Scope

This manifest records local evidence for the cross-surface handoff closure
across CLI, doged, examples, Web Research workspace, and governance docs.

## Implementation Evidence

| Area | Evidence |
|---|---|
| ADR | `docs/architecture/adr-0038-cross-surface-handoff-closure.md` records the decision. |
| CDD | `design/cdd/sprint-029-cross-surface-handoff-closure.md` records acceptance criteria. |
| CLI export | `src/doge/interfaces/cli/commands/export.py` exports Markdown, JSON, citations-only output, and file output from local persisted runs. |
| CLI parser | `src/doge/interfaces/cli/main.py` registers `doge export`. |
| CLI run hints | `src/doge/interfaces/cli/commands/run.py` prints human next actions for non-JSON output. |
| doged diagnostics | `src/doge/interfaces/daemon/main.py` implements `runs --status`, `explain`, and `support-bundle`. |
| Examples | `examples/.env.example`, `examples/README.md`, `examples/python/Makefile`, `examples/typescript/package.json`, and `examples/typescript/tsconfig.json`. |
| Web evidence | `web/src/utils/evidenceSourceType.ts` and `ConclusionEvidenceMatrix.vue` render source-type tags inside evidence chips. |
| Web approvals | `web/src/components/approval/ApprovalExplanation.vue` is used by Research and Case approval panels. |
| Web first-run | `web/src/components/agent/FirstRunGuide.vue` adds a browser-local first-run guide. |
| Web guided flow | `web/src/components/agent/GuidedFlow.vue` derives done/running/pending/missing states from existing stores. |
| CLI docs | `docs/CLI.md` documents `doge export`, run next actions, and doged diagnostics. |
| Tests | `tests/cli/test_cli_export.py`, `tests/cli/test_cli_run.py`, `tests/cli/test_cli_arg_parsing.py`, `tests/cli/test_doged_cli.py`, `tests/unit/sdk/test_sdk_cookbooks.py`, and targeted Web specs. |

## Verification Commands

```bash
py -3 -m pytest tests/cli/test_cli_export.py tests/cli/test_cli_run.py tests/cli/test_cli_arg_parsing.py tests/cli/test_doged_cli.py tests/unit/sdk/test_sdk_cookbooks.py -q
cd web && npm run test -- --run src/components/approval/ApprovalExplanation.spec.ts src/components/agent/ConclusionEvidenceMatrix.spec.ts src/components/agent/GuidedFlow.spec.ts src/components/agent/FirstRunGuide.spec.ts src/components/case/CaseApprovalPanel.spec.ts src/views/ResearchAgentView.spec.ts src/utils/evidenceSourceType.spec.ts
cd web && npm run build
py -3 tools/ci/sdk-contract-check.py
py -3 scripts/validate_docs_authority.py
py -3 scripts/validate_docs_links.py
py -3 scripts/validate_docs_maturity_claims.py
py -3 scripts/validate_import_boundaries.py
py -3 scripts/validate_alpha_maturity_honesty.py --file docs/architecture/adr-0038-cross-surface-handoff-closure.md
py -3 scripts/validate_alpha_maturity_honesty.py --file design/cdd/sprint-029-cross-surface-handoff-closure.md
py -3 scripts/validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/a038a698-harmonic-mango.md
git diff --check
```

## Verification Results

| Gate | Result |
|---|---|
| CLI/doged/example focused Python suite | Passed: 54 tests, 2 FastAPI deprecation warnings. |
| Web focused suite | Passed: 21 tests. |
| Full Web suite | Passed: 31 files, 143 tests. |
| Web build | Passed. |
| SDK contract | Passed: 15 surfaces, 15 entity parity checks. |
| Docs authority | Passed. |
| Docs links | Passed: 96 markdown files validated. |
| Docs maturity claims | Passed. |
| Import boundaries | Passed. |
| ADR/CDD maturity guard | Passed for ADR-0038 and Sprint 029 CDD. |
| Plan closure | Passed with controlled open posture: 4 open / 2 passed. |
| Whitespace | Passed with Windows Git `diff --check`. |

## Posture

- Production posture unchanged.
- No external/operator gates are closed by this sprint.
- No `/v1` route, SDK package source, persistence schema, or production
  readiness declaration is part of this sprint.
