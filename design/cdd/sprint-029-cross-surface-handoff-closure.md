# Sprint 029 CDD: Cross-Surface Handoff Closure

Status: Ready for Acceptance
Date: 2026-07-06

## User Promise

A Local Alpha user can move from running research to handing off results across
CLI, Web, daemon operator tools, and SDK examples without reading architecture
docs first.

## Delivered Contract

Sprint 029 implements the plan in
`C:\Users\WSMAN\.claude\plans\a038a698-harmonic-mango.md`:

- `doge export <run_id>` exports local persisted run summaries as Markdown or
  redacted JSON, including a citations-only mode.
- Human `doge run` output shows `Next actions:` while JSON and JSONL output
  remain unchanged.
- `doged runs --recent --status <status>` filters local run summaries.
- `doged explain <run_id>` prints safe failure context and next actions.
- `doged support-bundle --output <zip>` writes redacted local diagnostics.
- `examples/.env.example`, `examples/README.md`, `examples/python/Makefile`,
  and TypeScript example package wrappers document runnable cookbook paths.
- `ConclusionEvidenceMatrix.vue` renders source-type tags inside evidence
  chips without adding a new matrix column.
- `ApprovalExplanation.vue` reuses the same explanation DOM in Research and
  Case approval panels.
- `GuidedFlow.vue` derives done/running/pending/missing states from existing
  store data.
- `FirstRunGuide.vue` gives first-time Research workspace users a browser-local
  guide and stores dismissal in localStorage.
- `docs/CLI.md` documents the new CLI and operator commands.

## Non-Goals

- No `/v1` route, field, or route-count change.
- No SDK package source or public-surface change.
- No persistence migration or new runtime dependency.
- No remote operator admin API.
- No memo editing/versioning.
- No production gate closure.
- Current maturity posture remains `production_ready: false`,
  `stable_declaration: forbidden`, and Level 3 `experimental`.

## Acceptance Criteria

- `doge export` returns Markdown by default, supports JSON, supports
  citations-only, writes `--output`, redacts JSON, and returns exit code 1 for
  missing runs.
- `doge run` prints next actions for human output and preserves JSON/JSONL
  machine output.
- `doged runs --status`, `doged explain`, and `doged support-bundle` pass
  focused CLI tests.
- Support bundle zip entries include readiness, features, routes, queue,
  failed runs, redacted config, and version metadata.
- Example scaffolding tests assert daemon URL and cookbook wrapper metadata.
- Evidence source-type utility distinguishes document, tool, note, and fallback
  records.
- Research and Case approval panels render shared explanation rows in a
  deterministic order and omit blank rows.
- GuidedFlow renders four steps and derives done/running/pending/missing states
  without new store fields.
- FirstRunGuide shows for an empty first workspace, persists dismissal, and
  stays hidden when a run already exists.
- Docs and maturity validators keep Local Alpha posture honest.

## Validation Plan

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

## Local Verification Result

Final local verification passed. CLI/doged/example focused Python tests, full
Web tests, Web build, SDK contract parity, docs authority/links/maturity
validators, import boundaries, ADR/CDD honesty checks, plan closure, and
whitespace checks all passed. Evidence is recorded in
`production/qa/evidence/sprint-029-cross-surface-handoff-closure-manifest.md`.

## Out of Scope

- SDK high-level `create_memo` helper.
- Web memo editor/version history.
- Operator TUI.
- New API routes or production readiness work.
