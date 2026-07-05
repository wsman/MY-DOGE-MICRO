# Sprint UX-1 CDD: First-Run Coherence & Honest Maturity Disclosure

> **Status**: Ready for Acceptance — UX-1 local acceptance residue tracked to closure
> **Author**: Claude implementation agent
> **Last Updated**: 2026-07-05
> **Governing ADRs**: ADR-0028 (additive session-turn `workflow` field); references ADR-0007, ADR-0011, ADR-0018, ADR-0019, ADR-0021
> **Runtime Posture**: `production_ready: false`, `stable_declaration: forbidden`, `level_1_embedded_cli_session: alpha`, `level_2_daemon_gateway: alpha`, `level_3_sdk_platform: experimental` (Level 3 `experimental`) — unchanged
> **Plan**: `C:\Users\WSMAN\.claude\plans\agent-sharded-lagoon.md`

## Overview

Sprint UX-1 makes the platform's first-run experience coherent and honest. A
single `doge start` launcher routes operators to the five things they actually
want to do; every run status reads as a human sentence in every surface (CLI
REPL, web, `doge doctor`); the Web Research Workspace becomes a numbered
four-step guided flow backed by the four shipped scenario templates; and a
`MaturityPanel` states the runtime is Local Alpha with four open
production-readiness gates. The sprint is strictly additive — the only
wire/contract touch is the optional `workflow` field on
`POST /v1/sessions/{session_id}/turns` (ADR-0028); there is no SDK breaking
signature change, no CLI exit-code change, and no external-gate closure.

## User Promise / JTBD

As a first-time operator, I install the platform and reach a guided, green demo
run in under five minutes; at every step the system states run status in plain
English (never a raw enum), recommends a concrete next step when a check fails,
and honestly flags that this is Local Alpha software — never claiming
production-readiness. As a returning analyst, the scenario template I pick in
the Web workspace is the scenario the run actually uses.

## Detailed Behavior

Per-slice behavior is complete for local UX-1 acceptance. External production
gates remain controlled-open and are not closed by this sprint.

- **Slice 0 — Plan hygiene + contract classification.** (DONE: plan passes
  `validate_alpha_maturity_honesty.py`; paths reconciled; workflow-field
  contract classified and recorded as ADR-0028.)
- **Slice A — Run-status → human-label map.** A single canonical map translates
  each `RunStatus` member (`src/doge/core/domain/agent_models.py:19-27`:
  CREATED, QUEUED, RUNNING, AWAITING_APPROVAL, CANCELLING, CANCELLED, COMPLETED,
  FAILED) into a human label, a Naive-UI tag tone, and an aria-live sentence.
  Lives as a TS util `web/src/utils/runStatus.ts` (`labelFor`, `toneFor`,
  `sentenceFor`) and a Python twin
  `src/doge/interfaces/cli/run_status_labels.py` (dict keyed by
  `RunStatus.value`) so CLI `/status` and `doge doctor --next` reuse the same
  vocabulary. Labels: CREATED→"Preparing", QUEUED→"Queued", RUNNING→"Running",
  AWAITING_APPROVAL→"Waiting on your approval", CANCELLING→"Cancelling",
  CANCELLED→"Cancelled", COMPLETED→"Completed", FAILED→"Failed"; idle (no run)
  → "Idle". Unknown enum values fall through to `"Status: <raw>"`. Replaces the
  inline `statusType()` computeds in `ResearchAgentView.vue` and
  `ExecutionMonitor.vue` (`RunDetailView.vue` shows coverage/claims/citations
  rather than run status, so no run-status migration is needed there); a repo
  grep gate enforces zero raw run-status enum strings across all three views
  as a regression guard.
- **Slice B — `doge start` 5-path launcher.** A first-run launcher subcommand.
  With a TTY and no `--path`, it prints a numbered menu of the five main paths
  (Local CLI session / Start daemon / Open Web workspace / Run demo / Check
  readiness) and prompts for a choice; with no TTY (CI/subprocess) it prints the
  menu and exits 0 without prompting. `--path {cli,daemon,web,demo,doctor}`
  selects non-interactively. `demo` and `doctor` dispatch inline to `cmd_demo`/
  `cmd_doctor`; `cli`/`daemon`/`web` print the exact command (routing guidance)
  rather than spawning a nested interactive loop or long-running daemon.
  `doge start` itself never exits non-zero; an unknown `--path` is rejected by
  argparse (exit 2); an inlined `demo`/`doctor` propagates its own documented
  exit code.
- **Slice C — `doge doctor --next`.** Adds environment-aware next-step guidance.
  JSON mode gains an additive top-level `guidance: [{check, next_steps[]}]`
  array (existing `status`/`checks`/`critical_checks` untouched; JSON without
  `--next` is byte-identical to pre-Slice-C). Text mode prints a `next:` block
  per failing check after the existing `name=status` lines. Guidance is a
  static per-check-name table (`_NEXT_STEPS` in `doctor.py`) covering config,
  database_paths, tracked_views_sql (points at the version-controlled
  `src/doge/infrastructure/database/views.sql`), agent_database,
  document_storage, and model_provider_configuration. Exit code is unchanged
  (1 on not_ready, 0 on ok). `doge start --path doctor` now dispatches with
  `next=True` so the launcher's doctor path matches its displayed
  `doge doctor --next` command.
- **Slice D — REPL `/status` + grouped `/help`.** `/status` prints a one-line
  context `ses=<id> docs=<N> portfolio=<id|-> last_run=<id|none> pending=<N>`,
  where `pending` is tracked from the last embedded run's pending approvals
  (updated after each embedded turn, `/approve`, and `/cancel`; gateway mode is
  best-effort — last known value, since gateway stream events are not captured
  into the count — operators use `/trace` for live gateway approvals). `/help`
  prints grouped commands: Files (`/attach`, `/portfolio`), Tools (`/tools`),
  Run (`/trace`, `/artifacts`, `/cancel`), Approval (`/approve`, `/deny`),
  Session (`/new`, `/resume`, `/save`, `/status`, `/exit`). Pure additive
  branches in `session_interactive.interactive_loop`; no existing command
  semantics change.
- **Slice E — MaturityPanel.** `web/src/components/common/MaturityPanel.vue`
  (WEB-8) renders honest Local-Alpha disclosure: Runtime Level ("Local Alpha"),
  a provider line derived from the `/v1/capabilities` snapshot
  (`provider.kimi`/`provider.deepseek` `available` → "<Name> (live)", otherwise
  "scripted fallback (local_demo)"; "unknown" when the snapshot is absent), and
  the 4 open production-readiness gates (S017-003 / W3-live / AUTH-prod /
  S017-007) as static advisory copy sourced verbatim from
  `runtime-maturity.yaml` (not capability metadata, to keep the
  `CapabilityResponse` ↔ `Capability` ENTITY_PARITY contract untouched). The
  panel self-loads the snapshot (`onMounted` + `.catch`); vocabulary is locked
  to alpha-safe terms (no "production-ready"/"stable"/"GA"). Mounted in the
  ResearchAgentView quality pane.
- **Slice I — Workflow-slug plumbing (ADR-0028).** Threads an optional
  `workflow: str = "investment_research"` through the daemon turn path so a
  caller-selected workflow reaches the persisted `AgentRun`: added to
  `CreateTurnRequest` (gateway router), `SubmitSessionTurnCommand` (handler);
  `SubmitSessionTurnHandler` forwards it to `AsyncioWorker.enqueue_run` (the
  daemon worker class); the worker forwards it to `enqueue_run_and_turn`
  (replacing the `worker.py:129` literal); `ExecuteRun.execute` forwards it to
  `runtime.create_run` (replacing
  the `run_use_cases.py:35` literal). Defaults preserve `investment_research`
  (byte-for-byte current behavior). `AgentRun.workflow` and the two lower UoW
  layers are unchanged (already accept `workflow`). SDK `Session.run` gains an
  explicit optional `workflow` param (Python sync+async; TS type-only —
  `...rest` already forwarded it). Web `createAgentRun` forwards
  `payload.workflow` (previously dropped). `payload.workflow` stays
  `'investment_research'` until Slice G's ScenarioPicker replaces the
  `stores/agent.ts:27` literal.
- **Slice G — ScenarioPicker (frontend; depends on Slice I).**
  `web/src/components/agent/ScenarioPicker.vue` (WEB-10 frontend half) renders
  the four shipped named templates (Market Morning Brief / Earnings Quality
  Review / Portfolio Risk Review / Investment Committee Memo) as an `n-select`
  bound to a new `selectedScenarioSlug` ref in the agent store (default
  `investment_committee_memo`). `startDemoRun` now passes
  `workflow: selectedScenarioSlug.value` instead of the hard-coded
  `'investment_research'` literal (`stores/agent.ts:27`); with Slice I's
  threading, the selected slug drives the persisted `AgentRun.workflow`. The
  four slugs/labels are hardcoded in the picker (matching `template_seed.py`),
  no network dependency. Mounted at the top of the ResearchAgentView input
  pane. A repo grep gate (`test_no_hardcoded_workflow_in_agent_store.py`)
  enforces no `'investment_research'` literal returns to the store.
- **Slice F — Empty-state CTAs.** `web/src/components/agent/EmptyStateCtas.vue`
  (WEB-3) replaces the bare "No memo generated" placeholder in the memo pane
  with four getting-started CTAs: **Run Demo** (→ `store.startDemoRun`),
  **Load Sample Case** (→ selects the `earnings_review` scenario + scrolls to
  input), **Upload Documents** and **Import Portfolio** (→ scroll the input
  pane into view where the uploader/importer live). Each emits a distinct event
  the parent wires to an existing flow. The empty-state renders only when no
  memo is present; with a memo it is hidden (existing behavior unchanged).
- **Slice H — 4-step GuidedFlow.** `web/src/components/agent/GuidedFlow.vue`
  (WEB-7) renders a 4-step status rail (Add Evidence → Add Portfolio → Ask
  Question → Review Memo). Each step's done/pending status is derived from
  existing store state (document selection, portfolio id, question + run
  started, produced memo). Clicking a step emits `select(stepId)`; the parent
  (ResearchAgentView) scrolls to the relevant pane (steps 1-3 → input pane,
  step 4 → memo pane). Mounted at the top of the ResearchAgentView input pane.
  Pure UX orchestration over existing state — adds no new inputs.

## Contracts / Data Model

Additive only. The single wire/contract touch is the optional `workflow` field
on `POST /v1/sessions/{session_id}/turns` (ADR-0028). New internal surfaces:
`web/src/utils/runStatus.ts` + Python twin
`src/doge/interfaces/cli/run_status_labels.py`; new Web components
`MaturityPanel.vue`, `GuidedFlow.vue`, `ScenarioPicker.vue`,
`EmptyStateCtas.vue`; new CLI `doge start` + `doge doctor --next` flag + REPL
`/status` `/help`. No SDK breaking signature change; no CLI exit-code change;
no OpenAPI change beyond ADR-0028. The Web launcher guidance treats
`127.0.0.1:8901` as the daemon/API port and `127.0.0.1:5173` as the default
Vite workspace URL.

## Edge Cases

Covered edge cases: non-TTY `doge start`; capability-snapshot fetch failure
falls back to provider "unknown"; `/status` before any run prints an idle
context; unknown `RunStatus` values render as `Status: <raw>`; runs persisted
before Slice I keep `'investment_research'`; daemon/web launch failures remain
operator-visible command guidance rather than spawned child-process errors; and
ScenarioPicker works from the shipped four-template list without a network
dependency.

## Dependencies

Dependencies: `template_seed.py` (4 named templates); capability registry
(`src/doge/application/capabilities/registry.py`); `RunStatus` enum
(`src/doge/core/domain/agent_models.py:19-27`); ADR-0028; existing CLI
dispatch (`src/doge/interfaces/cli/main.py`); existing Web panes/stores; and
the local daemon/Vite split documented in `web/vite.config.ts`.

## Configuration Knobs

Configuration remains pre-existing: `DOGE_DAEMON_PORT`,
`DOGE_AUTH_MODE=local_demo`, `DOGE_ALLOW_DEMO_RUNTIME=1`, provider API keys,
and Vite's default development port. UX-1 adds no new env vars or settings
flags.

## Acceptance Criteria

Item-scoped; BLOCKING unless marked ADVISORY. Filled per slice as it is
implemented.

- **Slice A (BLOCKING):** `web/src/utils/runStatus.ts` exposes
  `labelFor`/`toneFor`/`sentenceFor` covering all 8 `RunStatus` members + idle
  + unknown fallback; `web/src/utils/runStatus.spec.ts` asserts label/tone
  parity across all 8 values + unknown fallback;
  `src/doge/interfaces/cli/run_status_labels.py` enumerates exactly the 8
  `RunStatus` members (pinned by
  `tests/unit/interfaces/test_run_status_labels.py`); repo grep gate asserts
  zero raw run-status enum strings in `ResearchAgentView.vue`,
  `ExecutionMonitor.vue`, `RunDetailView.vue`; the three inline `statusType()`
  computeds are removed.
- **Slice B (BLOCKING):** `doge start` subparser registered with `--path
  {cli,daemon,web,demo,doctor}`; `tests/cli/test_cli_start.py` asserts the menu
  renders all 5 paths, non-TTY stdin never hangs, `--path demo`/`doctor`
  dispatch inline (mocked), `--path cli|daemon|web` print guidance without
  dispatch, unknown `--path` exits 2; `tests/cli/test_cli_exit_codes.py`
  regression passes (no new exit code introduced by `start`).
- **Slice C (BLOCKING):** `doge doctor --next` adds an additive JSON
  `guidance[]` (one entry per failing check with a known next-step) and a text
  `next:` block; JSON without `--next` is byte-identical to pre-Slice-C;
  `tests/cli/test_cli_doctor.py` asserts guidance content, the byte-identical
  guarantee, the text block, and the unchanged exit code (1 on not_ready).
- **Slice D (BLOCKING):** REPL `/status` prints the one-line context
  `[ses | docs=N | portfolio | last_run | pending=N]` (pending tracked from the
  last embedded run's approvals) and `/help` prints grouped commands
  (Files/Tools/Run/Approval/Session); `tests/cli/test_cli_session.py` asserts
  both, including pending-count tracking after a turn.
- **Slice E (ADVISORY):** `MaturityPanel.vue` renders Runtime Level (Local
  Alpha), a live-or-scripted provider line derived from the capability
  snapshot, and the 4 open production-readiness gates as advisory copy; mounted
  in `ResearchAgentView`; `web/src/components/common/MaturityPanel.spec.ts`
  asserts Local Alpha, the provider line, the 4 gate IDs, and the absence of
  promotion language. `ResearchAgentView.spec.ts` mocks the platform store.
- **Slice I (BLOCKING):** per ADR-0028, optional `workflow` threads
  `CreateTurnRequest` → `SubmitSessionTurnCommand` → `SubmitSessionTurnHandler`
  → `AsyncioWorker.enqueue_run` → `IAgentUnitOfWork.enqueue_run_and_turn` and
  `ExecuteRun.execute` → `runtime.create_run`; defaults preserve
  `investment_research`; `tests/contract/test_session_turn_workflow.py` asserts
  OpenAPI exposure + per-layer threading (default + non-default);
  `tools/ci/sdk-contract-check.py` asserts the workflow token on all three
  client surfaces.
- **Slice G (ADVISORY):** `ScenarioPicker.vue` renders the 4 shipped templates
  bound to the store's `selectedScenarioSlug` (default
  `investment_committee_memo`); `startDemoRun` passes
  `workflow: selectedScenarioSlug.value`; `ScenarioPicker.spec.ts` asserts the 4
  options, the default, and write-through; BLOCKING grep gate
  `test_no_hardcoded_workflow_in_agent_store.py` asserts no `'investment_research'`
  literal in `stores/agent.ts`.
- **Slice F (ADVISORY):** `EmptyStateCtas.vue` renders 4 getting-started CTAs
  (Run Demo / Load Sample Case / Upload Documents / Import Portfolio) replacing
  the bare "No memo generated" placeholder; wired in ResearchAgentView to
  `startDemoRun`, `earnings_review` scenario selection, and input-pane scroll;
  `EmptyStateCtas.spec.ts` asserts the 4 CTAs render and emit.
- **Slice H (ADVISORY):** `GuidedFlow.vue` renders the 4-step rail
  (Add Evidence → Add Portfolio → Ask Question → Review Memo) with per-step
  status derived from store state; mounted in ResearchAgentView; clicking a
  step emits `select` and the view scrolls to the relevant pane;
  `GuidedFlow.spec.ts` asserts the 4 steps, status reflection, and select emit.
  `validate_alpha_maturity_honesty.py --file <plan>` + repo alpha/docs
  validators must stay green.

## Resolved Decisions

- **WEB-10 backend scope**: thread `workflow` end-to-end via ADR-0028 rather
  than frontend-only (user decision 2026-07-04).
- **Verification reduced Slice I scope**: the two lower persistence layers
  (`IAgentUnitOfWork`, `SQLiteAgentUnitOfWork`) already accept `workflow`; only
  the four upper layers + SDK explicit param + Web forwarding need changes.
- **Line-drift corrections**: hard-coded literal is at `web/src/stores/agent.ts:27`
  (not `agent.ts:26`); `agent.ts:30-41` `createAgentRun` declares then drops
  `workflow`.
- **MaturityPanel open-gate IDs**: static Alpha disclosure copy sourced from
  `runtime-maturity.yaml` (not capability-metadata extension, to avoid
  `CapabilityResponse`↔`Capability` ENTITY_PARITY churn).
