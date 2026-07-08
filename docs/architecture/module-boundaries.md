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
- Legacy `/api/*` and in-memory runtime are compatibility/demo surfaces under
  ADR-0024. The former PyQt dashboard, `doge.application.composition`, and
  `doge.application.agent.tools` were removed in Sprint M.
- Legacy router implementations live under `doge.interfaces.api_legacy.routers`;
  `doge.interfaces.api.routers` is a compatibility shim only.
- Daemon `/v1/*` router implementations live under `doge.interfaces.gateway.routers`;
  `doge.interfaces.api.routers.v1` is a compatibility shim only.
- Tool registry implementations live under `doge.application.tools`; the former
  `doge.application.agent.tools` shim was removed in Sprint M.
- The slot contract (`doge.platform.slots`) is a pure package: it imports only
  `doge.core.*`, `doge.shared.*`, and the standard library, and must not import
  `doge.config`, `doge.infrastructure`, `doge.adapters`, `doge.products`,
  `doge.application.tools`, `doge.application.agent`, `doge.bootstrap`, or
  `doge.interfaces`. Slot facet dataclasses in
  `doge.platform.slots.facets` therefore carry strings, mappings, callables, and
  `Any` rather than framework/runtime concrete types. Built-in slot providers
  live beside their product code when there is a product owner (e.g.
  `doge.products.market.slot.MarketCoreSlot` groups the market-facing tool
  descriptors; ADR-0059 adds `doge.products.portfolio.slot.PortfolioCoreSlot`,
  `doge.products.research.slot.EvidenceCoreSlot`, and
  `doge.products.quant.slot.QuantLabSlot` for product-owned tool grouping),
  beside platform code when the platform context owns the behavior (e.g.
  `doge.platform.workspace.slot.WorkflowTemplatesSlot` wraps the built-in
  workflow-template seed definitions,
  `doge.platform.governance.slot.ToolGovernancePolicySlot` wraps tool
  entitlement/approval policy,
  `doge.platform.governance.actions_slot.GovernanceActionsSlot` and
  `doge.platform.governance.compliance_slot.ComplianceScreeningSlot` wrap
  governance-owned tool descriptors, and
  `doge.platform.runtime.slot.RuntimeEventWatcherSlot` wraps runtime event
  watcher behavior), beside infrastructure code when the provider wraps a
  concrete infrastructure implementation (e.g.
  `doge.infrastructure.documents.slot.LocalDocumentParserSlot` wraps the local
  document parser, and
  `doge.infrastructure.data_source.slot.TDXDataSourceSlot` /
  `YFinanceDataSourceSlot` wrap market data-source adapters), beside interface
  code when the provider wraps a concrete route surface (e.g.
  `doge.interfaces.gateway.slot.SlotDiscoveryGatewaySlot` wraps the read-only
  `/v1/slots` router), beside eval code when the provider wraps deterministic
  local evaluation assets (e.g. `doge.eval.slot.LocalEvalCasesSlot` wraps the
  offline local cases file), beside workspace platform code when the provider
  wraps UI/workflow metadata (e.g.
  `doge.platform.workspace.ui_slot.ResearchWorkspaceUISlot` wraps Research
  workspace panel metadata), or in bootstrap when they wrap runtime/infrastructure
  wiring without a product owner (e.g.
  `doge.bootstrap.runtime_factories.builtin_model_slot.ModelKimiAgentSdkSlot`).
  Slot-aware wiring lives in `doge.bootstrap.runtime_factories.slots` behind
  `DOGE_FEATURE_SLOT_PLATFORM`, with `SlotKernel`/`SlotPolicy`/`SlotBundle`/
  `SlotLifecycle` and `SlotEnforcementPolicy` contracts in
  `doge.platform.slots`. `SlotLoader` loads JSON manifests as manifest-only
  slots for discovery/policy diagnostics; it must not import provider
  entrypoints until a separate third-party install/signing decision exists.
  Bundle activation is persisted through the bootstrap/API/CLI wiring and its
  repository port, not product modules. Third-party slot install preview may copy validated JSON
  manifests into the configured install directory, but those slots stay
  manifest-only; provider entrypoint execution remains blocked until a separate
  sandbox/signing decision exists. ADR-0058 makes the controlled built-in
  consumer path default-on, and ADR-0060 makes manifest-only loader activation
  controls default-on locally; install, enforcement, UI slot metadata, and
  provider execution remain separately gated. ADR-0059 adds domain-level built-in
  tool-slot ownership without moving provider implementations or changing
  `/v1/tools` parity. See ADR-0042, ADR-0043,
  ADR-0044, ADR-0046, ADR-0047, ADR-0048, ADR-0049, ADR-0050, ADR-0051,
  ADR-0052, ADR-0053, ADR-0054, ADR-0055, ADR-0056, ADR-0057, ADR-0058,
  ADR-0059, and ADR-0060.
- ADR-0027 is the controlling sunset policy for compatibility shims. Shim files
  may re-export, delegate, warn, and preserve documented compatibility symbols
  only; they must not gain new behavior ownership.

## Scenario Map

Sprint G reduces the public product language to the four `doge.products.*`
packages. Gateway and Eval are **not** product modules — Gateway is the Level-2
daemon runtime layer (`doge.interfaces.gateway`) and Eval is the quality
subsystem (`doge.eval`); see [index.md](../index.md) ("delivery channels and
adapters are not counted modules").

| Product Module | Package | Owns | Does Not Own |
|----------------|---------|------|--------------|
| Market | `doge.products.market` | Market data, scans, breadth, RSRS, anomalies, ticker metadata, market reports. | Research/portfolio/quant ownership, runtime orchestration, UI state. |
| Portfolio | `doge.products.portfolio` | Holdings, portfolio import, exposure, concentration, risk, scenario analysis. | Market-data maintenance, research workflows, concrete model SDKs. |
| Quant | `doge.products.quant` | Analytical views, read-only SQL execution, bounded Python analysis, factors/backtest/data-job extensions. | Product workflow orchestration, ungoverned code execution. |
| Research | `doge.products.research` | Macro/company/industry/earnings research, memos, notes, research tool workflows. | Market-data maintenance, Web UI state, production auth. |

The eight ADR-0021 bounded contexts (Market Intelligence, Research, Portfolio &
Risk, Quant & Data Lab, Workspace & Workflow, Agent Runtime, Knowledge &
Evidence, Governance & Evaluation) remain the internal architecture-governance
vocabulary — see Context Contracts below. The four product modules above are
the code-package / external-naming view; runtime, gateway, and eval concerns
map to the Agent Runtime, Knowledge & Evidence, and Governance & Evaluation
contexts.

> **Cross-reference:** the persona labels in the map below (Local Quant
> Operator / Researcher-Portfolio Manager / Enterprise Integrator / Eval-Demo
> Owner) are an architecture-composition view of the **5 reader paths** in
> [user-scenarios.md](../product/user-scenarios.md) — Local Quant Operator ≈
> Local Analyst; Researcher/PM ≈ Research Workspace; Enterprise Integrator ≈
> SDK Integrator + Daemon Operator; Eval/Demo Owner = Eval/Demo Owner. Labels
> are retained for cross-reference stability; new docs should prefer the
> reader-path names.

| Scenario | User Goal | Contexts Composed | Primary Entrypoints |
|----------|-----------|-------------------|---------------------|
| Local Quant Operator | Inspect breadth, momentum, ticker, anomaly, local DB, and macro-report signals. | Market Intelligence, Quant & Data Lab, Governance & Evaluation | CLI, MCP, Web Market, legacy scanner compatibility |
| Researcher / Portfolio Manager | Produce or review evidence-backed market/company/industry research and approval-ready artifacts. | Research, Portfolio & Risk, Knowledge & Evidence, Agent Runtime, Workspace & Workflow, Governance & Evaluation | Web Research, `doge session`, `/v1` runs |
| Enterprise Integrator | Embed runtime/gateway capabilities through API, SDK, MCP, and SSE contracts. | Agent Runtime, Workspace & Workflow, Knowledge & Evidence, Governance & Evaluation | `/v1`, SDKs, MCP, remote CLI |
| Eval / Demo Owner | Reproduce cases, inspect traces, and measure deterministic task quality. | Governance & Evaluation, Agent Runtime, Knowledge & Evidence | `doge batch`, eval runner, trace/report artifacts |

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
| In-memory runtime | Demo/test only | Production-facing flows use persisted runtime. | After deterministic test alternatives exist. |
| Scripted model | Demo/test only | Production-facing flows use live model adapters. | Separate support/removal story. |

### Known Boundary Tensions

- `doge.interfaces.api.routers.v1.run_stream` intentionally re-exports
  `RunStreamHandler` for legacy/static checks, but canonical live SSE behavior
  remains in `doge.interfaces.gateway.routers.run_stream` plus the handler
  layer. No stream behavior may be implemented in the shim.
- `doge.application.composition` and `doge.application.agent.tools` were removed
  in Sprint M; bootstrap containers and `doge.application.tools` are canonical.
- In-memory runtime is demo/test-only. Production-facing runtime evidence must
  use persisted repositories, durable queue, worker, and gateway paths.
