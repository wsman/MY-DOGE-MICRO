# Product Overview

MY-DOGE-MICRO is a local-first quantitative investment decision-support
platform. It helps an operator inspect market conditions, run scans, organize
research, review portfolio/risk context, and preserve evidence for AI-assisted
research workflows.

## Primary Users

- A local operator running analysis from a desktop, terminal, browser, or MCP
  client.
- A developer maintaining the local API, CLI, web, SDK, and MCP surfaces.
- A governance reviewer checking that maturity claims match evidence.

## Primary Scenarios

The product surface is organized around four primary user scenarios. See
[user-scenarios.md](user-scenarios.md) for the full scenario contract.

| Scenario | Primary contexts | Surfaces |
|----------|------------------|----------|
| Market Scan | Market Intelligence, Quant & Data Lab, Governance & Evaluation | Web Market, CLI, MCP, scanner compatibility |
| Research Memo | Research, Workspace & Workflow, Agent Runtime, Knowledge & Evidence, Governance & Evaluation | Web Research, `/v1` runs, SDK, CLI |
| Portfolio Risk | Portfolio & Risk, Market Intelligence, Governance & Evaluation | Web Portfolio, agent tools, portfolio APIs |
| Governed Agent Workflow | Workspace & Workflow, Agent Runtime, Knowledge & Evidence, Governance & Evaluation | Web Workspace, `/v1` cases/templates/runs, SDK |

Underlying capabilities such as document evidence, capability discovery,
archive browsing, and admin review remain available, but they are presented as
parts of these scenarios rather than as separate product modules.

## Local-First Boundary

SQLite stores local operational data. DuckDB provides analytical reads over
local views. External market/model providers are optional adapters and must be
configured explicitly by the operator.

Secrets belong in the shell environment or a configured secret provider, not in
committed files. The repository model config keeps
`REPLACE_WITH_DEEPSEEK_API_KEY` as a placeholder only.

## Maturity

The product is not declared production-ready. Runtime maturity is governed by
[../progress/runtime-maturity.yaml](../progress/runtime-maturity.yaml), which
currently keeps `production_ready: false` and
`stable_declaration: forbidden`.
