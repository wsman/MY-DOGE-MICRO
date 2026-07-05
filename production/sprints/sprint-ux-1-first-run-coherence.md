# Sprint UX-1 — First-Run Coherence & Honest Maturity Disclosure

> Status: **Local Implementation Complete / Ready for Local Acceptance**
> Branch: `main` · Date: 2026-07-05 · Baseline HEAD: `364d8fb`
> Plan: `C:\Users\WSMAN\.claude\plans\agent-sharded-lagoon.md`
> CDD: [design/cdd/sprint-ux-1-first-run-coherence.md](../../design/cdd/sprint-ux-1-first-run-coherence.md)
> ADR: [ADR-0028](../../docs/architecture/adr-0028-additive-session-turn-workflow-field.md)
> Predecessor: Sprint 021 (Narrative Reconciliation & Docs Hygiene)

## Context

UX-1 closes the first-run Local Alpha experience for the production-shaped
Agent Runtime sample without changing production posture. The sprint turns the
existing CLI / daemon / SDK / Web workspace into a coherent first-run path:
operators can choose a path from `doge start`, receive actionable readiness
guidance from `doge doctor --next`, inspect REPL context with `/status`, start a
Web guided flow from scenario templates and empty-state CTAs, and see honest
Local Alpha maturity disclosure in the Research Workspace.

The only wire-contract addition is ADR-0028's optional
`POST /v1/sessions/{session_id}/turns.workflow` field. It is additive, defaults
to `investment_research`, and threads through the turn handler, worker,
execute-run use case, SDKs, and Web store so a selected scenario slug reaches
the persisted `AgentRun.workflow`.

The acceptance residue found during review was also closed: Web launcher
guidance now opens the Vite dev server at `127.0.0.1:5173` instead of the
daemon/API port `8901`; the plan-closure gate can report the current
`agent-sharded-lagoon.md` source plan through `--source-plan` while preserving
the old default; the UX-1 CDD is no longer a draft skeleton; and ADR-0028's
validation checklist was updated after verification.

## Posture (unchanged)

- `production_ready: false`; `stable_declaration: forbidden`; `level_3_sdk_platform: experimental`.
- External gates S017-003 / W3-live / AUTH-prod / S017-007 remain open / operator-owned.
- No external evidence was fabricated; local UX evidence does not close live/provider/analyst/auth/registry gates.

## Slices

### Slice 0 — Plan hygiene + contract classification
- `agent-sharded-lagoon.md` remains validator-safe for Alpha maturity wording.
- `design/cdd/sprint-ux-1-first-run-coherence.md` is `Ready for Acceptance` and records the local UX-1 contract/posture boundaries.
- ADR-0028 is Accepted as the additive workflow-field decision.

### Slice A — Shared run-status labels
- Web and CLI share human-facing run-status vocabulary through `web/src/utils/runStatus.ts` and `src/doge/interfaces/cli/run_status_labels.py`.
- ResearchAgentView and ExecutionMonitor use the shared labels, tones, and live-region sentences instead of raw enum presentation.
- Architecture tests prevent raw run-status enum strings from returning to the target Web views.

### Slice B — `doge start`
- CLI first-run launcher routes to five paths: local CLI session, daemon, Web workspace, deterministic demo, and readiness check.
- Blocking paths print exact operator commands instead of spawning nested sessions or long-running daemons.
- Web path now points the browser to `http://127.0.0.1:5173`; `8901` remains the daemon/API port.

### Slice C — `doge doctor --next`
- Text mode appends actionable `next:` blocks for failing checks.
- JSON mode gains additive `guidance[]`; JSON without `--next` remains byte-identical.
- `doge start --path doctor` dispatches the next-step mode.

### Slice D — REPL `/status` and grouped `/help`
- Interactive sessions can show current session id, document count, portfolio id, last run id, and pending approvals.
- `/help` groups commands by Files, Tools, Run, Approval, and Session.
- Existing slash-command semantics remain additive.

### Slice E — Web MaturityPanel
- Research Workspace displays Local Alpha maturity, provider availability, and the four open production-readiness gates.
- The panel uses capability snapshot data for provider display and static runtime-maturity gate identifiers for posture disclosure.
- Promotion language remains absent.

### Slice I — Workflow slug plumbing
- Optional `workflow` threads through `CreateTurnRequest`, `SubmitSessionTurnCommand`, `AsyncioWorker.enqueue_run`, `ExecuteRun.execute`, SDK `Session.run`, Web API, and the agent store.
- Existing callers keep `investment_research`; selected Web scenarios can persist a specific workflow slug.
- SDK contract tooling verifies the request-body field.

### Slice G — ScenarioPicker
- Web Research Workspace exposes four shipped templates: Market Morning Brief, Earnings Quality Review, Portfolio Risk Review, and Investment Committee Memo.
- The selected scenario slug is passed into the run request instead of a hard-coded store literal.
- A grep-style architecture guard prevents reintroducing the hard-coded workflow in the Web store.

### Slice F — Empty-state CTAs
- The memo empty state now offers Run Demo, Load Sample Case, Upload Documents, and Import Portfolio actions.
- CTAs route into existing flows; no new runtime contract is added.

### Slice H — GuidedFlow
- The Research Workspace input area shows a four-step rail: Add Evidence, Add Portfolio, Ask Question, Review Memo.
- Step state is derived from existing document, portfolio, question/run, and memo state.
- Step clicks scroll to existing panes rather than introducing new state.

## Verification

- Python focused UX-1 suite: **29 passed, 2 warnings**
  (`tests/cli/test_cli_start.py`, `tests/unit/qa/test_validate_plan_closure_gate.py`,
  `tests/contract/test_session_turn_workflow.py`,
  `tests/unit/architecture/test_no_hardcoded_workflow_in_agent_store.py`,
  `tests/unit/architecture/test_no_raw_run_status_in_web.py`,
  `tests/unit/interfaces/test_run_status_labels.py`).
- Web regression: **110 passed** (`npm run test`); Web build **passed** (`npm run build`).
- Docs/governance: `validate_alpha_maturity_honesty.py --file C:/Users/WSMAN/.claude/plans/agent-sharded-lagoon.md` **passed**; `validate_docs_links.py` **86 markdown files validated**; `validate_docs_maturity_claims.py` **passed**; `validate_docs_authority.py` **passed**.
- Contract/boundary: `validate_import_boundaries.py` **passed**; `tools/ci/sdk-contract-check.py` **passed** (13 surfaces, 12 entity parity).
- Plan closure: `validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/agent-sharded-lagoon.md` **acceptable open**, 4 open / 2 passed / 0 failed / 0 invalid; runtime posture errors `[]`.
- Whitespace: `git diff --check` and Windows Git `diff --check` **clean**.

## Non-Goals

- No production posture promotion.
- No external-gate closure.
- No non-additive `/v1` or SDK public contract change.
- No `production/sprint-status.yaml` update; UX-1 is recorded as a completed local acceptance sprint, not a new story-bearing sprint.
- No UX-2 work.

## External Gates (unchanged)

S017-003 (financial provider approval), W3-live (analyst benchmark), AUTH-prod
(enterprise production validation), and S017-007 (SDK registry release) remain
open / operator-owned. UX-1 closes no external gate.
