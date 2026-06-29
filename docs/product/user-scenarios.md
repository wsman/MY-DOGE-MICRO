# User Scenarios

MY-DOGE-MICRO is organized around four primary scenarios. These are scenario
contracts, not new bounded contexts. Per ADR-0021, recurring scenarios should
compose existing capabilities and workflow templates.

## Market Scan

- **User**: local operator reviewing daily or weekly market conditions.
- **Problem**: identify momentum, breadth, anomaly, and ticker context without
  switching between scripts and reports.
- **Included capabilities**: RSRS ranking, breadth, volume anomalies, ticker
  lookup, market archives, scanner compatibility workflow.
- **Excluded capabilities**: memo drafting, portfolio rebalance approval, live
  trading, production broker execution.
- **Entrypoints**: Web Market, scanner deep link, CLI, MCP market tools.
- **Bounded contexts**: Market Intelligence, Quant & Data Lab, Governance &
  Evaluation.
- **Workflow-template relationship**: a Market Scan template may compose scan
  inputs, market, filters, and evidence output but does not create a new module.

## Research Memo

- **User**: operator or research assistant preparing a market, company, or
  industry note.
- **Problem**: combine research context, local evidence, AI assistance, and
  citation preservation in one auditable flow.
- **Included capabilities**: macro/industry report use cases, notes, document
  evidence, RAG lookup, claims/citations, agent runs.
- **Excluded capabilities**: ungrounded investment advice, undisclosed source
  claims, live provider evidence without operator credentials.
- **Entrypoints**: Web Research, Research Agent deep link, `/v1` run APIs,
  Python/TypeScript SDK clients, CLI session/run commands.
- **Bounded contexts**: Research, Workspace & Workflow, Agent Runtime,
  Knowledge & Evidence, Governance & Evaluation.
- **Workflow-template relationship**: a Research Memo template defines inputs,
  required evidence, allowed tools, output memo contract, and eval profile.

## Portfolio Risk

- **User**: operator reviewing holdings exposure or preparing a risk scenario.
- **Problem**: understand portfolio concentration, shocks, and high-risk actions
  before publishing or proposing changes.
- **Included capabilities**: portfolio CSV import, exposure review, risk service,
  scenario analysis, rebalance proposal tool.
- **Excluded capabilities**: brokerage order placement, managed-account
  execution, production compliance sign-off.
- **Entrypoints**: Web Portfolio, portfolio/risk agent tools, `/v1` portfolio
  APIs where available.
- **Bounded contexts**: Portfolio & Risk, Market Intelligence, Governance &
  Evaluation.
- **Workflow-template relationship**: a Portfolio Risk template composes
  holdings, market context, scenario assumptions, approval requirements, and
  audit output.

## Governed Agent Workflow

- **User**: operator or developer running and auditing agent-assisted work.
- **Problem**: run, approve, inspect, and preserve agent workflows without
  bypassing tenant, tool, evidence, or maturity policy.
- **Included capabilities**: workspaces, projects, research cases, workflow
  templates, sessions, runs, events, approvals, artifacts, audit exports,
  capability registry, maturity status.
- **Excluded capabilities**: production live-gate completion without operator
  evidence, ungoverned model/tool calls, direct persistence edits from UI.
- **Entrypoints**: Web Workspace, `/v1` cases/templates/runs, SDK clients, CLI.
- **Bounded contexts**: Workspace & Workflow, Agent Runtime, Knowledge &
  Evidence, Governance & Evaluation.
- **Workflow-template relationship**: the scenario is itself the governed
  workflow-template path; new workflows should extend templates and policy
  metadata rather than adding runtime modules.
