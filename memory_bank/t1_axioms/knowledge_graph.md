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

## Docs Index (comprehensive)

Every `docs/` subtree is indexed by the memory_bank tier recorded in
`document_map.yaml`. Content stays in `docs/`; this section is the navigable
map (an index, not a duplicate).

| docs/ path | Purpose | Indexed by (tier) |
|---|---|---|
| [../../docs/index.md](../../docs/index.md) | Documentation entrance + reader-path table | T1 knowledge_graph |
| [../../docs/architecture/](../../docs/architecture/) | ADRs, runtime contracts, module boundaries, compatibility surfaces, control manifest, traceability, registry | T1 architecture_context |
| [../../docs/progress/](../../docs/progress/) | `runtime-maturity.yaml` (machine authority), current-status | T0 current_state; T1 knowledge_graph |
| [../../docs/reference/](../../docs/reference/) | API/CLI/MCP/env-var/configuration shortcuts + VERSION snapshots | T1 tech_context |
| [../../docs/API.md](../../docs/API.md) · [../../docs/CLI.md](../../docs/CLI.md) · [../../docs/MCP_SERVER.md](../../docs/MCP_SERVER.md) | Product reference content homes | T1 tech_context |
| [../../docs/product/](../../docs/product/) | Overview, modules, user scenarios, runtime levels | T1 behavior_context |
| [../../docs/guides/](../../docs/guides/) · [../../docs/start-here/](../../docs/start-here/) · [../../docs/operations/](../../docs/operations/) | Operational how-to, reader paths, runbook | T2 workflow_contract |
| [../../docs/quality/](../../docs/quality/) | Generated status, eval metrics, test matrix, validation scripts | T1 qa_context |
| [../../docs/governance/cdd/](../../docs/governance/cdd/) | CDD framework (workflow guide, user manual, quick-start, acceptance) | T2 workflow_contract |
| [../../docs/security-and-data-boundaries.md](../../docs/security-and-data-boundaries.md) · [../../docs/registry/architecture.yaml](../../docs/registry/architecture.yaml) | Security/data-boundary authority; architecture registry | T1 architecture_context |
| [../../docs/demo/](../../docs/demo/) | Kimi SA demo scripts, storyboards, data | T3 qa_evidence_index |
| [../../docs/archive/](../../docs/archive/) | Historical audits, superseded docs | T3 qa_evidence_index |

## Critical Integrations

- MCP tools expose local read-only market and research workflows through stdio/SSE.
- FastAPI exposes local HTTP and daemon/v1 runtime routes.
- Web and SDK clients consume the FastAPI/daemon surfaces.
- Document evidence and RAG services ground agent outputs in local evidence.
- Portfolio/risk/scenario/industry-report tools extend Research Copilot capability while preserving deterministic or evidence-aware status.
