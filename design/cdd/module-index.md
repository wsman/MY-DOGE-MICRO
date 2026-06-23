# Module Index: MY-DOGE-MICRO

> **Status**: In Review
> **Created**: 2026-06-11
> **Last Updated**: 2026-06-23
> **Source Concept**: design/cdd/product-concept.md
> **Consolidation Baseline**: docs/progress/platformization-consolidation-baseline.md
> **Governing ADRs**: ADR-0001, ADR-0021, ADR-0022

---

## Overview

MY-DOGE-MICRO is a local-first quantitative investment decision-support
platform with market intelligence, research, portfolio/risk, quant analysis,
agent runtime, evidence, workflow, and governance capabilities.

The previous module index mixed three dimensions in one counted list:

- technical layers such as Core, Application, Infrastructure, and Interface;
- product capabilities such as market, research, portfolio, evidence, and
  agent work;
- delivery or adapter surfaces such as API, Web, CLI, SDK, MCP, PyQt, SQLite,
  DuckDB, model providers, and market data providers.

ADR-0021 proposes the Phase A consolidation: the counted product/platform
module list is now eight bounded contexts. The former 20 mixed modules are
preserved in the appendix as detailed design inputs and migration references,
but they are no longer the canonical counted module set.

Runtime maturity remains explicitly non-production:

- Level 1: Preview
- Level 2: Alpha
- Level 3: Experimental
- Production Ready: false
- Stable Declaration: forbidden

---

## Canonical Bounded Context Enumeration

| # | Bounded Context | Type | Status | Design Doc | Primary Owner | Depends On |
|---|-----------------|------|--------|------------|---------------|------------|
| 1 | Market Intelligence | Product | In Review | design/cdd/bc-01-market-intelligence.md | python-specialist, lead-programmer | Governance & Evaluation, adapters |
| 2 | Research | Product | In Review | design/cdd/bc-02-research.md | lead-programmer, python-specialist | Workspace & Workflow, Agent Runtime, Knowledge & Evidence, Governance & Evaluation |
| 3 | Portfolio & Risk | Product | In Review | design/cdd/bc-03-portfolio-risk.md | python-specialist, security-engineer | Market Intelligence, Governance & Evaluation, adapters |
| 4 | Quant & Data Lab | Product | In Review | design/cdd/bc-04-quant-data-lab.md | python-specialist, performance-analyst | Governance & Evaluation, adapters |
| 5 | Workspace & Workflow | Platform | In Review | design/cdd/bc-05-workspace-workflow.md | lead-programmer, python-specialist | Agent Runtime, Knowledge & Evidence, Governance & Evaluation |
| 6 | Agent Runtime | Platform | In Review | design/cdd/bc-06-agent-runtime.md | lead-programmer, python-specialist | Governance & Evaluation, Knowledge & Evidence, adapters |
| 7 | Knowledge & Evidence | Platform | In Review | design/cdd/bc-07-knowledge-evidence.md | python-specialist, qa-lead | Agent Runtime, Governance & Evaluation, adapters |
| 8 | Governance & Evaluation | Platform | In Review | design/cdd/bc-08-governance-evaluation.md | lead-programmer, security-engineer | shared primitives, adapters |

---

## Module Counting Rules

### Counted Modules

Only the eight bounded contexts above count as product/platform modules for
architecture planning, story grouping, and CDD coverage.

### Delivery Channels

These are entrypoints and client surfaces, not counted modules:

```text
FastAPI
Web
CLI
Daemon
SDK
MCP
PyQt
```

### Adapters

These are concrete implementations behind ports, not counted modules:

```text
SQLite
DuckDB
TDX
yfinance
akshare
Kimi
DeepSeek
OpenAI-compatible clients
Vector stores
Eventing
Secrets
Persistence drivers
```

### Architecture Programs

Architecture or migration campaigns are governed workstreams, not counted
product modules:

```text
Clean Architecture Migration
Bounded Context Consolidation
Directory Restructuring
Legacy Deletion
```

---

## Former Mixed Module Appendix

The 20 historical rows remain useful as design evidence. They map into bounded
contexts, delivery channels, adapters, or governance programs as follows:

| Former # | Former Module | New Classification | Target Owner |
|----------|---------------|--------------------|--------------|
| 1 | Runtime Configuration | Shared / Bootstrap | shared, bootstrap |
| 2 | Market Data Storage | Persistence Adapter | adapters/persistence |
| 3 | TDX/YFinance Data Sources | Market Data Adapter | adapters/market_data |
| 4 | Macro Strategy Engine | Product Context | Research |
| 5 | Micro Momentum Scanner | Product Context | Market Intelligence |
| 6 | Market Reporting | Product Context | Market Intelligence |
| 7 | Research Insight Knowledge Base | Split Product/Platform | Research, Knowledge & Evidence |
| 8 | MCP Server | Delivery Channel | entrypoints/mcp |
| 9 | FastAPI Service | Delivery Channel | entrypoints/api |
| 10 | PyQt Desktop Dashboard | Legacy Delivery Channel | entrypoints/pyqt |
| 11 | Vue Web Console | Delivery Channel | web/ |
| 12 | Clean Architecture Migration | Architecture Program | architecture governance |
| 13 | Research Copilot Agent Runtime | Platform Context | Agent Runtime |
| 14 | Document Evidence Pipeline | Platform Context | Knowledge & Evidence |
| 15 | SDK And Daemon Client Interfaces | Delivery Channel | packages/, entrypoints/daemon |
| 16 | Run Summary Citation API | Platform Query API | Knowledge & Evidence |
| 17 | Workspace Project Research Case | Platform Context | Workspace & Workflow |
| 18 | Workflow Templates | Platform Context | Workspace & Workflow |
| 19 | Platform Shell UI | Delivery Channel | web/ |
| 20 | Capability Registry | Shared Platform Contract | Workspace & Workflow, Governance & Evaluation |

---

## Categories

| Category | Description | Examples |
|----------|-------------|----------|
| Product Context | Durable user-facing capability domain | Market Intelligence, Research, Portfolio & Risk, Quant & Data Lab |
| Platform Context | Shared product infrastructure with business semantics | Workspace & Workflow, Agent Runtime, Knowledge & Evidence, Governance & Evaluation |
| Delivery Channel | How users or clients access capabilities | API, Web, CLI, SDK, MCP, PyQt |
| Adapter | Concrete provider, persistence, or integration implementation | SQLite, DuckDB, Kimi, TDX, yfinance |
| Architecture Program | Governance or migration workstream | Clean Architecture Migration, Directory Restructuring |

---

## Dependency Map

### Product Contexts

1. Market Intelligence depends on market-data and persistence adapters through
   ports, and on Governance & Evaluation for policy.
2. Research depends on Workspace & Workflow for case/template context, Agent
   Runtime for execution, Knowledge & Evidence for source grounding, and
   Governance & Evaluation for policy.
3. Portfolio & Risk depends on Market Intelligence for price/market contracts
   and Governance & Evaluation for high-risk action policy.
4. Quant & Data Lab depends on Governance & Evaluation for budget/sandbox
   policy and on adapters through analytical ports.

### Platform Contexts

1. Workspace & Workflow organizes Workspace, Project, Research Case, Workflow
   Template, and case-run relationships.
2. Agent Runtime coordinates sessions, runs, events, workers, model execution,
   tool execution, artifacts, and cancellation.
3. Knowledge & Evidence owns documents, pages, chunks, retrieval, claims,
   citations, provenance, run summaries, and eval read models.
4. Governance & Evaluation owns identity, tenant, ACL, entitlement, approval,
   audit, secrets, budget, eval, and maturity gates.

### Boundary Rule

Product contexts communicate through public capability contracts. Runtime and
entrypoints call ports/application services. Adapters do not contain business
decisions. Only bootstrap/composition roots wire concrete implementations.

---

## Recommended Design and Migration Order

| Order | Workstream | Purpose | Gate |
|-------|------------|---------|------|
| 1 | ADR-0021 review | Approve or revise the eight-context boundary model | Architecture review |
| 2 | ADR-0022 review | Approve or revise facade-first package restructuring | Import compatibility strategy |
| 3 | Control Manifest update | Enforce bounded-context import and transition rules | Governance tests |
| 4 | Provider Registry migration | Close ToolApplicationService dual path | Provider parity tests |
| 5 | RuntimeKernel split | Extract model, tool, and artifact/eval services | Runtime unit and contract tests |
| 6 | Platform router extraction | Move route orchestration into services | Platform API contract tests |
| 7 | Web information architecture | Collapse old/new navigation into one product shell | Web tests and accessibility evidence |
| 8 | Legacy removal | Delete deprecated paths after removal gates close | Full suite and migration audit |

---

## High-Risk Areas

| Area | Risk Type | Risk Description | Mitigation |
|------|-----------|------------------|------------|
| Runtime maturity | Product/Governance | Platform features may be mistaken for production readiness. | Keep `docs/progress/runtime-maturity.yaml` authoritative and block stable claims. |
| Tool dual path | Architecture | Provider Registry and direct execution can become permanent parallel systems. | Set parity tests, default Provider Registry on, then delete old branches. |
| Platform router | Architecture | HTTP routers can absorb business orchestration. | Move workspace/project/case/workflow logic into application services. |
| RuntimeKernel | Architecture | Coordinator can become a second god service. | Split model, tool, and artifact/eval execution services. |
| Web navigation | UX/Product | Legacy and platform navigation can present two products. | Make Platform Shell primary and redirect legacy Research Agent route after gates. |
| Directory migration | Regression | Big-bang moves can break imports and SDK contracts. | Follow ADR-0022 facade-first migration and compatibility tests. |
| Governance gates | Release | Open external gates can be overlooked. | Keep external gate audit and maturity file blocking promotion. |

---

## Latest Governance Sync

- ADR-0012 records the enterprise model gateway and Kimi routing boundary.
- ADR-0013 records financial tool governance, entitlement categories, and
  high-risk approval handling.
- ADR-0014 records multimodal financial evidence and citation provenance.
- ADR-0015 proposes the enterprise identity/access boundary for OIDC/JWT,
  tenant ACLs, approval actor, audit actor, and secrets handling.
- ADR-0016 proposes user-level workspace/project/research-case objects with
  association tables and no nullable runtime/evidence context columns by
  default.
- ADR-0017 proposes server-authoritative run summary, claim, citation, and eval
  APIs under `/v1/runs/{run_id}`.
- ADR-0018 proposes versioned workflow templates and governed execution
  records.
- ADR-0019 proposes redacted capability discovery for providers, tools,
  workflows, evidence, UI, APIs, and runtime maturity.
- ADR-0020 proposes a feature-flagged platform shell while preserving direct
  `/research-agent` compatibility.
- ADR-0021 proposes the eight bounded-context consolidation recorded in this
  index.
- ADR-0022 proposes the facade-first target directory restructuring strategy.
- TR-055 through TR-058 add enterprise identity requirements across FastAPI,
  runtime, document evidence, and SDK/daemon client CDDs.
- TR-059 through TR-070 add platformization requirements for run summaries,
  user-level objects, templates, shell UI, capability registry, and maturity
  guardrails.

---

## Progress Tracker

| Metric | Count |
|--------|-------|
| Canonical bounded contexts identified | 8 |
| Bounded-context CDDs started | 8 |
| Bounded-context CDDs reviewed | 0 |
| Bounded-context CDDs approved | 0 |
| Former mixed modules preserved as appendix | 20 |
| Delivery channels excluded from counted modules | 7 |
| Adapter categories excluded from counted modules | 8+ |
| Proposed consolidation ADRs | 2 |
| Accepted consolidation ADRs | 0 |

---

## Next Steps

- [ ] Review and approve or revise the eight bounded-context enumeration.
- [ ] Review ADR-0021 before treating the new index as implementation
      authority.
- [ ] Review ADR-0022 before creating facade packages or moving source files.
- [ ] Keep ADR-0015 Proposed until OIDC/JWT, tenant ACL, approval actor, audit
      actor, and secrets handling implementation tests exist.
- [ ] Keep ADR-0016 through ADR-0020 Proposed until their first implementation
      slices and independent architecture review pass.
- [ ] Keep ADR-0021 and ADR-0022 Proposed until bounded-context docs,
      compatibility strategy, and independent architecture review pass.
- [ ] Run `/design-review` on each bounded-context CDD.
- [ ] Run `/architecture-review` after ADR and CDD coverage exists.
- [ ] Update story planning so new scenarios use Workflow Templates instead of
      creating new product modules.
