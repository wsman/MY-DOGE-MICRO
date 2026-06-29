# Module Boundaries

> Sprint E boundary contract for the ADR-0021 bounded-context model.
> Runtime maturity remains governed by `docs/progress/runtime-maturity.yaml`.

## Boundary Rules

- Product contexts do not import sibling product contexts directly.
- Runtime does not import product contexts directly.
- Entrypoints call application/platform services and bootstrap wiring; they do
  not open persistence adapters directly.
- Adapters implement ports and do not own business decisions.
- Bootstrap and compatibility composition roots own concrete wiring.
- Legacy `/api/*`, `doge.application.composition`, in-memory runtime, and PyQt
  are compatibility/demo surfaces under ADR-0024.
- Legacy router implementations live under `doge.interfaces.api_legacy.routers`;
  `doge.interfaces.api.routers` is a compatibility shim only.
- Daemon `/v1/*` router implementations live under `doge.interfaces.gateway.routers`;
  `doge.interfaces.api.routers.v1` is a compatibility shim only.
- Tool registry implementations live under `doge.application.tools`;
  `doge.application.agent.tools` is a compatibility shim only.

## Scenario Map

| Scenario | User Goal | Contexts Composed | Primary Entrypoints |
|----------|-----------|-------------------|---------------------|
| Market Scan | Inspect breadth, momentum, ticker, and anomaly signals. | Market Intelligence, Quant & Data Lab, Governance & Evaluation | Web Market, CLI, MCP, legacy scanner compatibility |
| Research Memo | Produce or review evidence-backed market/company/industry research. | Research, Knowledge & Evidence, Agent Runtime, Workspace & Workflow, Governance & Evaluation | Web Research, `/v1` runs, SDK, CLI |
| Portfolio Risk | Import holdings and review exposure, risk, scenarios, or rebalance proposals. | Portfolio & Risk, Market Intelligence, Governance & Evaluation | Web Portfolio, agent tools, `/v1` portfolio paths |
| Governed Agent Workflow | Run, inspect, approve, audit, and preserve agent work. | Workspace & Workflow, Agent Runtime, Knowledge & Evidence, Governance & Evaluation | Web Workspace, `/v1` runs/cases/templates, SDK |

## Context Contracts

### Market Intelligence

- **Owner**: `doge.products.market`
- **Public contract**: market scans, stock lookup, RSRS, breadth, anomalies,
  market reports, ticker metadata.
- **Owned data**: market scan result projections, ticker query contracts,
  market indicators.
- **May call**: core market ports/services, market-data adapters through ports,
  governance/capability policy, bootstrap-provided repositories.
- **Not allowed**: direct imports from Research, Portfolio, Quant, runtime
  implementation, or persistence drivers.
- **Legacy sources**: `src/micro`, market use cases under `doge.application`,
  legacy `/api/scan/*`.

### Research

- **Owner**: `doge.products.research`
- **Public contract**: macro, company, industry, earnings, memo, note, and
  research tool workflows.
- **Owned data**: research memo requests, industry report workflows, note/research
  contracts.
- **May call**: Workspace & Workflow for case context, Knowledge & Evidence for
  grounding, Agent Runtime for execution, Governance & Evaluation for policy.
- **Not allowed**: direct market/portfolio product imports outside public
  capability contracts.
- **Legacy sources**: macro/industry use cases and research providers under
  `doge.application`.

### Portfolio & Risk

- **Owner**: `doge.products.portfolio`
- **Public contract**: holdings, portfolio import, exposure, concentration,
  risk, scenario analysis, rebalance proposal contracts.
- **Owned data**: portfolio holdings, scenario inputs, risk summaries.
- **May call**: Market Intelligence contracts for price/market context and
  Governance & Evaluation for high-risk action policy.
- **Not allowed**: direct research or quant implementation imports.
- **Legacy sources**: portfolio application services and provider modules.

### Quant & Data Lab

- **Owner**: `doge.products.quant`
- **Public contract**: analytical views, read-only SQL execution, bounded Python
  analysis capability, factors/backtest/data-job extensions.
- **Owned data**: analytical request/response contracts and high-risk analysis
  metadata.
- **May call**: view services/repositories through ports and governance policy.
- **Not allowed**: unrestricted DB connections, ungoverned code execution, or
  product workflow orchestration.
- **Legacy sources**: quant provider under `doge.application.capabilities`.

### Workspace & Workflow

- **Owner**: `doge.platform.workspace`
- **Public contract**: workspace, project, research case, workflow template,
  case asset, case decision, execution, and capability catalog relationships.
- **Owned data**: workspaces, projects, cases, templates, case-run links,
  capability registry projections.
- **May call**: Agent Runtime for executions, Knowledge & Evidence for assets,
  Governance & Evaluation for tenant and policy.
- **Not allowed**: product-specific calculations or provider implementation.
- **Legacy sources**: platform application services and capability registry use
  case under `doge.application.use_cases`.

### Agent Runtime

- **Owner**: `doge.platform.runtime`
- **Public contract**: sessions, runs, events, worker queue, model execution,
  tool execution, artifact finalization, approvals, cancellation.
- **Owned data**: run/session/event contracts and runtime service protocols.
- **May call**: model, tool, artifact, eval, queue, and repository ports.
- **Not allowed**: direct product context imports or direct adapter business
  decisions.
- **Legacy sources**: runtime kernel, worker, run stepper, approval coordinator,
  transition recorder, and tool registry under `doge.application.agent`.

### Knowledge & Evidence

- **Owner**: `doge.platform.evidence`
- **Public contract**: documents, pages, chunks, evidence chunks, retrieval,
  claims, citations, run summaries, eval read models.
- **Owned data**: evidence records, document chunks/pages, claim/citation
  records, vector search records.
- **May call**: evidence/document/vector ports and runtime-provided run context.
- **Not allowed**: product decisions or ungoverned tenant data exposure.
- **Legacy sources**: evidence services and run-summary use cases under
  `doge.application`.

### Governance & Evaluation

- **Owner**: `doge.platform.governance`
- **Public contract**: identity, tenant context, ACL, entitlement, approvals,
  audit, secrets, model gateway, compliance/publishing tools, maturity gates.
- **Owned data**: enterprise context, principals, grants, audit events, approval
  actor decisions, maturity posture.
- **May call**: shared primitives, governance repositories, secret/model ports.
- **Not allowed**: workspace capability catalog ownership or product-specific
  calculations.
- **Legacy sources**: compliance and publishing providers plus enterprise
  governance ports/models.

## Compatibility Surface Sunset

| Surface | Status | Rule | Earliest Removal |
|---------|--------|------|------------------|
| Legacy `/api/*` | Compatibility | No new platform feature only under `/api/*`; deprecation headers required. | Not before 2026-09-30 and route parity evidence. |
| `doge.interfaces.api.routers` | Compatibility shim | New legacy-local router work uses `doge.interfaces.api_legacy.routers`; new gateway work uses `doge.interfaces.gateway.routers`. | After all internal and third-party imports migrate. |
| `doge.interfaces.api.routers.v1` | Compatibility shim | New `/v1` implementation work uses `doge.interfaces.gateway.routers`. | After API clients and tests no longer import the old v1 module path. |
| `doge.application.agent.tools` | Compatibility shim | New tool registry work uses `doge.application.tools`. | After runtime and test import parity evidence. |
| `doge.application.composition` | Compatibility shim | New internal platform work should use process roots/bootstrap. | After import parity and migration notes. |
| In-memory runtime | Demo/test only | Production-facing flows use persisted runtime. | After deterministic test alternatives exist. |
| PyQt dashboard | Legacy local surface | Web/SDK/v1 are preferred platform UX paths. | Separate support/removal story. |
