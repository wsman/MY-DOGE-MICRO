# Knowledge Graph

This is the canonical memory-bank knowledge graph path. The deprecated path
`memory_bank/t0_core/knowledge_graph.md` should not receive future updates.

## Module Dependency Sketch

Runtime Configuration -> Market Data Storage -> Data Sources -> Macro Strategy Engine
Runtime Configuration -> Market Data Storage -> Data Sources -> Micro Momentum Scanner
Market Data Storage -> Market Reporting -> Research Insight Knowledge Base
Research Insight Knowledge Base -> Document Evidence Pipeline -> Research Copilot Agent Runtime
Research Copilot Agent Runtime -> FastAPI Service -> SDK And Daemon Client Interfaces
FastAPI Service -> Vue Web Console
Macro Strategy Engine -> PyQt Desktop Dashboard
Micro Momentum Scanner -> PyQt Desktop Dashboard
Market Reporting -> PyQt Desktop Dashboard
Clean Architecture Migration -> all interface/core/infrastructure modules

## Current Nodes

| Node | Source | Status |
|------|--------|--------|
| Product concept | `design/cdd/product-concept.md` | designed |
| Module index | `design/cdd/module-index.md` | in review |
| CDD set | `design/cdd/*.md` | 15 modules documented; release follow-up modules in review |
| ADR set | `docs/architecture/adr-0001..0014*.md` | accepted |
| TR registry | `docs/architecture/tr-registry.yaml` | current |
| Runtime maturity | `docs/progress/runtime-maturity.yaml` | current; Stable forbidden |
| Sprint status | `production/sprint-status.yaml` | current |

## Critical Integrations

- MCP tools expose local read-only market and research workflows through stdio/SSE.
- FastAPI exposes local HTTP and daemon/v1 runtime routes.
- Web and SDK clients consume the FastAPI/daemon surfaces.
- Document evidence and RAG services ground agent outputs in local evidence.
- Portfolio/risk/scenario/industry-report tools extend Research Copilot capability while preserving deterministic or evidence-aware status.
