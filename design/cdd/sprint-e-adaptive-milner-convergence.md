# Sprint E CDD: Adaptive Milner Bounded-Context Convergence

> **Status**: Accepted
> **Author**: Codex implementation agent
> **Last Updated**: 2026-06-29
> **Review**: Lean design review approved on 2026-06-29; see `design/cdd/reviews/sprint-e-adaptive-milner-convergence-review-log.md`.
> **Governing ADRs**: ADR-0021, ADR-0022, ADR-0024
> **Runtime Posture**: `production_ready: false`, `stable_declaration: forbidden`, Level 3 `experimental`

## Overview

Sprint E turns the accepted eight bounded-context model into an enforceable
source, documentation, and Web navigation boundary. It does not add a new
market feature. It makes the existing Market Intelligence, Research, Portfolio
& Risk, Quant & Data Lab, Workspace & Workflow, Agent Runtime, Knowledge &
Evidence, and Governance & Evaluation contexts easier to navigate, test, and
extend without drifting back into legacy product/API splits.

## User Promise

When an operator or developer follows a market-analysis workflow, they should
see one product organized around four primary scenarios: Market Scan, Research
Memo, Portfolio Risk, and Governed Agent Workflow. When a developer adds code,
they should know which bounded context owns it, which imports are allowed, and
which legacy surfaces are compatibility-only. The payoff is lower architecture
ambiguity without removing working brownfield paths.

## Detailed Design

### Core Specification

1. Sprint E introduces a human-readable module boundary contract and a
   machine-readable ownership manifest.
2. Sprint E keeps physical source movement facade-first. New public imports are
   added through `doge.platform.*` and `doge.products.*`; old imports remain
   compatible.
3. Sprint E moves tool-provider discovery to owning context facades while
   preserving `doge.application.capabilities.*` as implementation and
   compatibility paths.
4. Sprint E narrows Web information architecture around Market, Research,
   Portfolio, and Workspace. Legacy deep links remain available.
5. Sprint E records any direct Web `/api/*` usage as either migrated to `/v1`
   or explicitly documented as an ADR-0024 compatibility exception.
6. Sprint E adds local gate tests for ownership, new-code imports, facade
   completeness, facade parity, tool-provider ownership, and Web legacy API
   usage.
7. Sprint E adds runtime maturity tracking without changing production or
   stable labels.

### States and Transitions

| State | Entry Condition | Exit Condition | Next State |
|-------|-----------------|----------------|------------|
| Proposed | CDD exists and QA scope is drafted. | QA plan and initial boundary docs exist. | In Implementation |
| In Implementation | Sprint E code/docs are being changed. | All focused Sprint E gates pass. | Verification |
| Verification | Implementation is complete locally. | Closure evidence records commands and results. | Accepted |
| Accepted | Focused gates pass and no new regression is recorded. | Future physical moves or legacy removal stories begin. | Superseded or Follow-up |

### Interactions with Other Modules

| Context | Sprint E Interaction | Owner of Contract |
|---------|----------------------|-------------------|
| Market Intelligence | Market scan scenario, market tools, scanner compatibility route. | `doge.products.market` |
| Research | Research Memo scenario, research/fundamental tool providers. | `doge.products.research` |
| Portfolio & Risk | Portfolio Risk scenario and portfolio tool provider. | `doge.products.portfolio` |
| Quant & Data Lab | SQL/Python analysis provider and analytical workbench classification. | `doge.products.quant` |
| Workspace & Workflow | Scenario composition, capability registry, cases, templates. | `doge.platform.workspace` |
| Agent Runtime | Run/session/event execution, model/tool/artifact services. | `doge.platform.runtime` |
| Knowledge & Evidence | Evidence chunks, documents, claims, citations, run summaries. | `doge.platform.evidence` |
| Governance & Evaluation | Auth, tenant, ACL, entitlement, audit, secrets, maturity, high-risk tools. | `doge.platform.governance` |

## Data Model

The Sprint E ownership manifest is the only new durable data artifact:

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `schema_version` | integer | Yes | `1` | Manifest parser version. |
| `generated_for` | string | Yes | `sprint-e-adaptive-milner` | Workstream owner. |
| `covered_roots` | array[string] | Yes | Repo-relative paths | Roots that must be owned by exactly one context. |
| `contexts` | object | Yes | Keyed by context slug | Ownership and import policy per context. |
| `path_patterns` | array[string] | Yes | Glob patterns | Files owned by the context. |
| `allowed_dependencies` | array[string] | Yes | Import roots | Expected dependencies. |
| `forbidden_dependencies` | array[string] | Yes | Import roots | Imports that fail Sprint E gates. |
| `compatibility_allowlist` | array[object] | No | Path + import + reason | Temporary exceptions with ADR/gate rationale. |

The file is stored as a JSON-compatible YAML document so tests can parse it
with the Python standard library instead of adding a PyYAML dependency.

## Edge Cases

- **If WSL Git reports broad modified files but Windows Git is clean**: classify
  with `git diff --ignore-cr-at-eol --shortstat` and do not create a baseline
  commit from CRLF noise.
- **If a facade export cannot preserve object identity**: keep the old import
  path and remove the new export until parity is restored.
- **If Web scanner has no `/v1` parity route**: keep the legacy route only as a
  named ADR-0024 compatibility exception and fail new unlisted `/api/*` uses.
- **If full regression still has pre-existing unrelated failures**: record them
  separately in closure evidence; Sprint E cannot introduce new failures.
- **If a high-risk tool lacks explicit risk metadata**: add the metadata at the
  descriptor/provider layer, not by hand-writing duplicate schemas.
- **If ownership manifest coverage is too broad for one sprint**: narrow
  `covered_roots` explicitly and record follow-up roots; do not silently skip.

## Dependencies

| Dependency | Direction | Type | Sprint E Use |
|------------|-----------|------|--------------|
| ADR-0021 | Input | Architecture | Defines the eight bounded contexts. |
| ADR-0022 | Input | Architecture | Requires facade-first migration and compatibility imports. |
| ADR-0024 | Input | Architecture | Defines `/v1` and SDK as preferred new platform paths. |
| `docs/progress/runtime-maturity.yaml` | Input/Output | Governance | Records Sprint E without maturity promotion. |
| `docs/architecture/control-manifest.md` | Input/Output | Governance | Receives new boundary and verification rules. |
| Existing facade tests | Input/Output | Verification | Extended for parity and completeness. |
| Existing Web route tests | Input/Output | Verification | Extended for four-scenario navigation. |

## Configuration

Sprint E introduces no runtime feature flags or operator secrets. Its only
configuration-like artifacts are governance documents and tests:

| Parameter | Default | Scope | Behavior |
|-----------|---------|-------|----------|
| `production_ready` | `false` | Runtime maturity | Must remain unchanged. |
| `stable_declaration` | `forbidden` | Runtime maturity | Must remain unchanged. |
| `module-ownership.schema_version` | `1` | Test parser | Fails if the manifest schema changes without test updates. |
| Web `/api/*` allowlist | explicit list | Web test | Only named ADR-0024 exceptions are accepted. |

## Integration Requirements

- Backend APIs are not expanded unless Web scanner parity already exists under
  `/v1`. If not, Sprint E documents the scanner exception instead of creating a
  partial API route.
- Web navigation changes preserve existing deep links and route names used by
  tests and saved URLs.
- Tool-provider facades preserve old class object identity so existing SDK,
  agent, and registry tests continue to pass.
- Closure evidence must distinguish local gate evidence from external/operator
  gate evidence.

## UI Requirements

- Primary Web navigation should expose Market, Research, Portfolio, and
  Workspace as the four scenario entrypoints.
- Home may remain available as a dashboard route, but it is not the governing
  scenario taxonomy.
- Quant and Admin may remain accessible as secondary workbench/governance
  views if tests and docs explain their placement.
- Deep links such as `/research-agent`, `/scanner`, `/analysis`, `/templates`,
  and `/runs` remain compatibility routes.

## Acceptance Criteria

- **GIVEN** the Sprint E worktree, **WHEN** the owner opens
  `docs/architecture/module-boundaries.md`, **THEN** every bounded context has
  an owner, public contract, allowed calls, forbidden calls, and legacy-source
  notes.
- **GIVEN** the Sprint E ownership manifest, **WHEN**
  `tests/unit/layer_gates/test_module_ownership.py` runs, **THEN** all covered
  files map to exactly one context and forbidden imports fail the test.
- **GIVEN** target facade packages, **WHEN** facade parity and completeness tests
  run, **THEN** public new imports resolve to the same objects as legacy imports.
- **GIVEN** Governance & Evaluation facade imports, **WHEN** a caller imports
  `BuildCapabilityRegistry`, **THEN** it is available from
  `doge.platform.workspace` and not from `doge.platform.governance`.
- **GIVEN** tool provider classes, **WHEN** ownership tests run, **THEN** market,
  research, portfolio, quant, and governance providers are importable from their
  owning `tools.py` modules while old capability imports still work.
- **GIVEN** the Web shell, **WHEN** route/navigation tests run, **THEN** Market,
  Research, Portfolio, and Workspace are the primary scenario entries and
  legacy deep links remain valid.
- **GIVEN** Web source files, **WHEN** the legacy API gate runs, **THEN** direct
  `/api/*` calls are either absent or named ADR-0024 compatibility exceptions.
- **GIVEN** runtime maturity data, **WHEN** Sprint E closes, **THEN**
  `sprint_e_adaptive_milner_convergence` is recorded without changing
  `production_ready` or `stable_declaration`.
- **GIVEN** local verification, **WHEN** closure evidence is written, **THEN** it
  records focused test counts, full-regression status, known unrelated failures
  if any, Windows Git status, and CRLF-noise classification.

## Open Questions

- Whether the legacy market scanner should receive a `/v1` parity route in this
  sprint or remain an ADR-0024 exception until a dedicated API story.
- Whether Quant remains a secondary top-level workbench or becomes a sub-panel
  under Market/Research after product review.
