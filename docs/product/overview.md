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

## Core Scenarios

| Scenario | Primary context | Surfaces |
|----------|-----------------|----------|
| Scan market momentum and breadth | Market Intelligence | CLI, API, Web, MCP, PyQt |
| Produce or review macro/company/industry research | Research | CLI, API, Web, PyQt |
| Upload documents and ground claims in citations | Knowledge & Evidence | API, Web, SDK |
| Track workspace/project/case organization | Workspace & Workflow | API, Web, SDK |
| Review portfolio exposure and scenarios | Portfolio & Risk | API, Web, agent tools |
| Run governed agent workflows | Agent Runtime | API, Web, SDK, CLI |
| Check capability and maturity status | Governance & Evaluation | API, Web, docs |

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
