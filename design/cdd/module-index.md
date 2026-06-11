# Module Index: MY-DOGE QUANT SYSTEM

> **Status**: Draft
> **Created**: 2026-06-11
> **Last Updated**: 2026-06-11
> **Source Concept**: design/cdd/product-concept.md

---

## Overview

MY-DOGE QUANT SYSTEM is a local-first product composed of data ingestion, local storage, quantitative analysis, AI-assisted interpretation, and multiple operator interfaces. The current brownfield implementation has working legacy modules and an in-progress clean architecture migration; the module plan below captures both current product capability and the migration path needed for CDD-controlled development.

---

## Module Enumeration

| # | Module Name | Category | Priority | Status | Design Doc | Depends On |
|---|-------------|----------|----------|--------|------------|------------|
| 1 | Runtime Configuration | Foundation | MVP | In Progress | design/cdd/runtime-configuration.md | None |
| 2 | Market Data Storage | Foundation | MVP | In Progress | design/cdd/market-data-storage.md | Runtime Configuration |
| 3 | TDX/YFinance Data Sources | Foundation | MVP | In Progress | design/cdd/data-sources.md | Runtime Configuration, Market Data Storage |
| 4 | Macro Strategy Engine | Core | MVP | In Progress | design/cdd/macro-strategy-engine.md | Market Data Storage, TDX/YFinance Data Sources |
| 5 | Micro Momentum Scanner | Core | MVP | In Progress | design/cdd/micro-momentum-scanner.md | Market Data Storage, TDX/YFinance Data Sources |
| 6 | AI Industry Analysis | Feature | Vertical Slice | In Progress | — | Macro Strategy Engine, Micro Momentum Scanner |
| 7 | Research Insight Knowledge Base | Core | MVP | In Progress | design/cdd/research-insight-knowledge-base.md | Market Data Storage, AI Industry Analysis |
| 8 | MCP Server | Interface | MVP | In Progress | design/cdd/mcp-server.md | Runtime Configuration, Market Data Storage, Research Insight Knowledge Base |
| 9 | FastAPI Service | Interface | Vertical Slice | In Progress | design/cdd/fastapi-service.md | Runtime Configuration, Market Data Storage, Macro Strategy Engine, Micro Momentum Scanner |
| 10 | PyQt Desktop Dashboard | Presentation | Vertical Slice | In Progress | — | Macro Strategy Engine, Micro Momentum Scanner, AI Industry Analysis |
| 11 | Vue Web Console | Presentation | Alpha | In Progress | — | FastAPI Service |
| 12 | Clean Architecture Migration | Operations | MVP | In Progress | design/cdd/clean-architecture-migration.md | Runtime Configuration, Market Data Storage |

---

## Categories

| Category | Description | Typical Modules |
|----------|-------------|-----------------|
| **Foundation** | Infrastructure and primitives other modules depend on | Runtime configuration, storage, data sources |
| **Core** | Modules required for the central market-analysis workflow | Macro strategy, micro momentum, research knowledge base |
| **Feature** | User-facing analytical workflows built on core modules | AI industry analysis |
| **Interface** | External access surfaces and protocols | MCP server, FastAPI service |
| **Presentation** | Human operator UI surfaces | PyQt dashboard, Vue web console |
| **Operations** | Architecture, quality, release, and migration control | Clean architecture migration |

---

## Priority Tiers

| Tier | Definition | Target Milestone | Design Urgency |
|------|------------|------------------|----------------|
| **MVP** | Required for current local-first workflow to function | Brownfield stabilization | Design first |
| **Vertical Slice** | Required for a complete operator path across analysis and UI | Modularized v1 slice | Design second |
| **Alpha** | Expanded surface area and workflow polish | Alpha product consolidation | Design third |
| **Full Vision** | Nice-to-have automation, observability, and broader integrations | Post-v1 | Design as needed |

---

## Dependency Map

### Foundation Layer

1. Runtime Configuration — centralizes paths, settings, and environment overrides.
2. Market Data Storage — owns SQLite/DuckDB local persistence and analytical views.
3. TDX/YFinance Data Sources — imports and refreshes market data.

### Core Layer

1. Macro Strategy Engine — depends on storage and external market/model access.
2. Micro Momentum Scanner — depends on storage and data source outputs.
3. Research Insight Knowledge Base — depends on storage and generated analysis artifacts.

### Feature Layer

1. AI Industry Analysis — depends on macro context, micro candidates, ticker calibration, and model clients.

### Interface Layer

1. MCP Server — exposes local tools for AI clients.
2. FastAPI Service — exposes HTTP API for web and other clients.

### Presentation Layer

1. PyQt Desktop Dashboard — operator-facing desktop workflow.
2. Vue Web Console — browser workflow through the API.

### Operations Layer

1. Clean Architecture Migration — cuts direct coupling and routes interfaces through services/ports.

---

## Recommended Design Order

| Order | Module | Priority | Layer | Agent(s) | Est. Effort |
|-------|--------|----------|-------|----------|-------------|
| 1 | Clean Architecture Migration | MVP | Operations | lead-programmer, python-specialist | M |
| 2 | Runtime Configuration | MVP | Foundation | python-specialist | S |
| 3 | Market Data Storage | MVP | Foundation | python-specialist | M |
| 4 | MCP Server | MVP | Interface | python-specialist, qa-lead | M |
| 5 | TDX/YFinance Data Sources | MVP | Foundation | python-specialist | M |
| 6 | Micro Momentum Scanner | MVP | Core | python-specialist | M |
| 7 | Macro Strategy Engine | MVP | Core | python-specialist | M |
| 8 | Research Insight Knowledge Base | MVP | Core | python-specialist | S |
| 9 | AI Industry Analysis | Vertical Slice | Feature | python-specialist, security-engineer | M |
| 10 | FastAPI Service | Vertical Slice | Interface | python-specialist | M |
| 11 | PyQt Desktop Dashboard | Vertical Slice | Presentation | ui-programmer, python-specialist | M |
| 12 | Vue Web Console | Alpha | Presentation | typescript-specialist, ui-programmer | M |

---

## Circular Dependencies

- Legacy code shows coupling between `micro`, `ai_analysis`, root MCP/API entrypoints, and database helpers. Resolve by routing interface modules through core services and infrastructure adapters.
- `macro/strategist.py` and `micro/industry_analyzer.py` currently interact across analysis concerns. Resolve with explicit report/analysis service contracts.

---

## High-Risk Modules

| Module | Risk Type | Risk Description | Mitigation |
|--------|-----------|------------------|------------|
| Clean Architecture Migration | Technical | New clean architecture files are untracked while legacy paths still run. | Freeze state in Git snapshot, write ADR, migrate in batches, preserve compatibility entrypoints. |
| Market Data Storage | Technical | Direct SQLite/DuckDB access is spread across interface and analysis modules. | Centralize repositories and connection management behind ports. |
| AI Industry Analysis | Technical/Product | Model output can hallucinate market claims. | Keep ticker metadata calibration, source grounding, retries, and cached fallback behavior. |
| Vue Web Console | Scope | Web UI expands product surface while backend migration is unfinished. | Keep web API contracts narrow until services stabilize. |

---

## Progress Tracker

| Metric | Count |
|--------|-------|
| Total modules identified | 12 |
| Design docs started | 1 |
| Design docs reviewed | 0 |
| Design docs approved | 0 |
| MVP modules designed | 0/8 |
| Vertical Slice modules designed | 0/3 |

---

## Next Steps

- [ ] Review and approve this module enumeration.
- [ ] Retrofit or author module CDDs for MVP modules.
- [ ] Run `/design-review` on each completed CDD.
- [ ] Run `/architecture-review` after ADR and CDD coverage exists.
- [ ] Run `/sprint-plan update` after sprint scope is confirmed.
