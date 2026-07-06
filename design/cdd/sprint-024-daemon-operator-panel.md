# Sprint 024 CDD: Daemon Operator Panel

Status: Ready for Acceptance
Date: 2026-07-05

## User Promise

A local operator can inspect daemon readiness, recent runs, queue state, feature
flags, and registered routes from `doged` without opening SQLite manually or
adding a public admin API.

## Delivered Contract

Sprint 024 implements the daemon operator panel batch from
`C:\Users\WSMAN\.claude\plans\agent-quizzical-wolf.md`:

- `doged doctor --verbose` prints nested readiness details from `/health/ready`.
- `doged runs --recent [--limit N] [--json]` prints bounded recent persisted
  runs.
- `doged queue --status [--json]` prints latest queue status counts.
- `doged features [--json]` prints feature flag values and lifecycle env vars.
- `doged routes [--json]` prints registered API method/path/name rows.
- `IRunQueue.status_summary()` and `SQLiteRunQueue.status_summary()` provide a
  shared latest-status queue summary.

## Non-Goals

- No `/v1/operator/*` route.
- No SDK method, SDK type, or SDK parity entry.
- No queue mutation, retry, cancellation, or dead-letter repair command.
- No remote admin panel.
- No change to readiness endpoint semantics.
- No external/operator gate closure.
- Current maturity posture remains `production_ready: false`,
  `stable_declaration: forbidden`, and Level 3 `experimental`.

## Acceptance Criteria

- `doged doctor --verbose` preserves existing doctor behavior and adds nested
  details in text mode.
- `doged doctor --json` remains unchanged.
- `doged runs --recent` prints run id, status, workflow, updated timestamp, and
  compact question text.
- `doged runs --recent --json` returns a `{"runs": [...]}` object.
- `doged queue --status` prints latest-status counts.
- `doged features` includes feature lifecycle env vars where available.
- `doged routes` lists method, path, and route name.
- Queue status summary follows latest queue row per run.
- Focused CLI and repository tests pass.
- Governance validators pass and closure posture remains controlled-open.

## Validation Plan

```bash
py -3 -m pytest tests/cli/test_doged_cli.py tests/contract/test_agent_repositories.py -q
py -3 tools/ci/sdk-contract-check.py
py -3 scripts/validate_docs_authority.py
py -3 scripts/validate_alpha_maturity_honesty.py --file README.md
py -3 scripts/validate_docs_links.py
py -3 scripts/validate_import_boundaries.py
py -3 scripts/validate_docs_maturity_claims.py
py -3 scripts/validate_alpha_maturity_honesty.py --file docs/architecture/adr-0033-local-daemon-operator-cli.md
py -3 scripts/validate_alpha_maturity_honesty.py --file design/cdd/sprint-024-daemon-operator-panel.md
py -3 scripts/validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/agent-quizzical-wolf.md
git diff --check
```

## Local Verification Result

- Initial focused Sprint 024 Python suite passed: 20 tests, 2 known FastAPI
  deprecation warnings.
- SDK contract check passed at 13 surfaces / 13 parity.
- Docs authority, README maturity, docs links, import boundaries, docs maturity
  claims, ADR/CDD/plan maturity guards, plan closure, and whitespace checks
  passed.
- Closure posture remained `4 open / 2 passed`.

## Out of Scope

- Portfolio path-depth improvements.
- SDK cookbook files.
- Demo pack generation.
- Run comparison.
- Governance workflow progress visualization.
