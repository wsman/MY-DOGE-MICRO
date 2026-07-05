# Sprint UX-2 CDD: Scenario Completion & Run-Readiness

> **Status**: Ready for Acceptance — local UX-2 implementation complete
> **Author**: Codex implementation agent
> **Last Updated**: 2026-07-05
> **Governing ADRs**: ADR-0018 (workflow templates), ADR-0019 (capabilities), ADR-0021 (bounded contexts), ADR-0028 (workflow slug)
> **Runtime Posture**: `production_ready: false`, `stable_declaration: forbidden`, `level_1_embedded_cli_session: alpha`, `level_2_daemon_gateway: alpha`, `level_3_sdk_platform: experimental` — unchanged
> **Plan**: `C:\Users\WSMAN\.claude\plans\agent-quizzical-wolf.md`

## Overview

UX-2 completes the scenario and run-readiness path started by UX-1. A first-time
operator should see `doge start` at the top of the README, choose a scenario in
the Web workspace without depending on a feature-flagged API being available,
understand run readiness before clicking Run, and use `doge brief` to turn
local market scan data into a compact market brief that can lead naturally into
a research memo.

The sprint is scoped to Local Alpha UX and CLI polish. It does not promote
runtime maturity, close external/operator gates, or change `/v1`/SDK contracts.

## User Promise / JTBD

As a local analyst or demo owner, I can reach a useful first result faster:

- `doge start` is visible before I choose a path.
- Scenario templates in the Web workspace reflect seeded workflow templates
  when available and remain usable when the template API is disabled.
- Before running, I can see whether market, evidence, portfolio, and provider
  inputs are ready or degraded.
- `doge brief --market cn` gives me a six-section market brief on stdout.

## Detailed Behavior

### README First-Run Pointer

README Quick Start shows:

```bash
pip install -e .
doge start
```

The surrounding copy explains the launcher routes to the local CLI session,
daemon gateway, Web workspace, deterministic demo, or readiness check. It does
not add new maturity vocabulary beyond the existing Local Alpha posture.

### ScenarioPicker Live-Browse

`ScenarioPicker.vue` renders options from `platformStore.workflowTemplates` when
that store has templates. On mount, if the store is empty, it calls
`loadWorkflowTemplates()`. Because `/v1/workflow-templates` defaults off behind
`DOGE_FEATURE_WORKFLOW_TEMPLATES`, load failures and empty results are treated
as expected degraded mode and the component renders the four UX-1 fallback
scenarios.

### Built-In Templates

The seed list includes two additional templates:

- `risk_alert`: event-driven risk signal, affected exposure, evidence, and
  action candidates.
- `portfolio_impact_note`: event summary, portfolio exposure, impact
  assessment, and investment committee questions.

Both are idempotent through `seed_workflow_templates()` and covered by the
workspace workflow seed tests.

### Run Preflight Checklist

`RunPreflightChecklist.vue` reads only existing stores:

- `agentStore.market`
- `documentStore.selectedIds`
- `agentStore.portfolioId`
- `platformStore.capabilitiesById['provider.kimi'].metadata.configured`

Missing documents, portfolio, or Kimi configuration render warnings. They do
not block Run, because portfolio and live provider configuration are optional
in the current Local Alpha degraded-mode posture.

### Console Market Brief

`GenerateMarketOverviewUseCase.brief()` renders a stdout-oriented Markdown
brief without writing a report file. Sections:

1. Market Regime
2. Breadth
3. Momentum Leaders
4. Volume Anomalies
5. Watchlist
6. Suggested Research Questions

`doge brief` defaults to `--market cn`. `--market us` exits non-zero with a
clear unavailable-data message because the current SQL path depends on local CN
views and must not fabricate US market brief data.

## Contracts / Data Model

- No `/v1` request or response contract changes.
- No SDK public-surface changes.
- No database migration.
- Built-in template seed data is additive and idempotent.
- `doge brief` is an additive CLI subcommand with documented exit behavior.

## Edge Cases

- Workflow template API disabled: ScenarioPicker falls back to four local
  scenarios.
- Workflow template list empty: ScenarioPicker falls back to four local
  scenarios.
- Capability snapshot missing: preflight provider status is unknown/warning and
  does not block.
- No documents selected: evidence warning, not a block.
- No portfolio imported: portfolio-risk warning, not a block.
- `doge brief --market us`: expected non-zero with a clear data-unavailable
  message.

## Dependencies

- `src/doge/platform/workspace/template_seed.py`
- `web/src/stores/platform.ts`
- `web/src/stores/agent.ts`
- `web/src/stores/documents.ts`
- `src/doge/application/capabilities/registry.py`
- `src/doge/application/use_cases/generate_market_overview.py`
- `src/doge/interfaces/cli/main.py`
- `docs/progress/runtime-maturity.yaml`

## Configuration Knobs

No new settings. Existing relevant knobs:

- `DOGE_FEATURE_WORKFLOW_TEMPLATES`
- provider API key env vars that affect capability metadata
- `DOGE_AGENT_DB` for template seed persistence

## Acceptance Criteria

- README Quick Start includes `doge start` before the three Platform Alpha path
  list and passes docs maturity/authority validation.
- ScenarioPicker renders templates from the platform store when present and
  falls back when the store is empty or loading fails.
- `risk_alert` and `portfolio_impact_note` seed idempotently and are visible in
  the workflow template repository.
- ResearchAgentView renders RunPreflightChecklist before Run; the checklist
  shows market/document/portfolio/provider checks without blocking degraded
  runs.
- `doge brief --market cn` prints all six section headers on stdout.
- `doge brief --market us` exits non-zero and states that US brief data is
  unavailable.
- Plan closure remains controlled-open at 4 open / 2 passed.

## Verification

Focused checks completed:

```text
py -3 -m pytest tests\cli\test_cli_brief.py tests\unit\workspace_workflow\test_template_seed.py tests\test_market_reporting.py tests\cli\test_cli_arg_parsing.py -q
=> 34 passed

cd web && npm run test -- src/components/agent/ScenarioPicker.spec.ts src/components/agent/RunPreflightChecklist.spec.ts src/views/ResearchAgentView.spec.ts
=> 9 passed

cd web && npm run build
=> passed
```

Docs/governance validators, import-boundary validation, SDK contract check, and
controlled-open plan closure passed after implementation.
