# Module Index: MY-DOGE QUANT SYSTEM

> **Status**: In Review
> **Created**: 2026-06-11
> **Last Updated**: 2026-06-21
> **Source Concept**: design/cdd/product-concept.md

---

## Overview

MY-DOGE QUANT SYSTEM is a local-first product composed of data ingestion, local storage, quantitative analysis, AI-assisted interpretation, document evidence extraction, Research Copilot agent runtime, and multiple operator/client interfaces. The current brownfield implementation has working legacy modules plus release-follow-up runtime slices; the module plan below captures both current product capability and the migration path needed for CDD-controlled development.

---

## Module Enumeration

| # | Module Name | Category | Priority | Status | Design Doc | Depends On |
|---|-------------|----------|----------|--------|------------|------------|
| 1 | Runtime Configuration | Foundation | MVP | Designed | design/cdd/runtime-configuration.md | None |
| 2 | Market Data Storage | Foundation | MVP | Designed | design/cdd/market-data-storage.md | Runtime Configuration |
| 3 | TDX/YFinance Data Sources | Foundation | MVP | Designed | design/cdd/data-sources.md | Runtime Configuration, Market Data Storage |
| 4 | Macro Strategy Engine | Core | MVP | Designed | design/cdd/macro-strategy-engine.md | Market Data Storage, TDX/YFinance Data Sources |
| 5 | Micro Momentum Scanner | Core | MVP | Designed | design/cdd/micro-momentum-scanner.md | Market Data Storage, TDX/YFinance Data Sources |
| 6 | Market Reporting | Feature | Vertical Slice | Designed | design/cdd/market-reporting.md | Runtime Configuration, Market Data Storage (writes `stock_names` shared with #7) |
| 7 | Research Insight Knowledge Base | Core | MVP | Designed | design/cdd/research-insight-knowledge-base.md | Market Data Storage, Market Reporting |
| 8 | MCP Server | Interface | MVP | Designed | design/cdd/mcp-server.md | Runtime Configuration, Market Data Storage, Research Insight Knowledge Base |
| 9 | FastAPI Service | Interface | Vertical Slice | Designed | design/cdd/fastapi-service.md | Runtime Configuration, Market Data Storage, Macro Strategy Engine, Micro Momentum Scanner |
| 10 | PyQt Desktop Dashboard | Presentation | Vertical Slice | Designed | design/cdd/pyqt-desktop-dashboard.md | Macro Strategy Engine, Micro Momentum Scanner, Market Reporting |
| 11 | Vue Web Console | Presentation | Alpha | Designed | design/cdd/vue-web-console.md | FastAPI Service |
| 12 | Clean Architecture Migration | Operations | MVP | Designed | design/cdd/clean-architecture-migration.md | Runtime Configuration, Market Data Storage |
| 13 | Research Copilot Agent Runtime | Core | Release Follow-Up | In Review | design/cdd/research-copilot-agent-runtime.md | Runtime Configuration, Market Data Storage, FastAPI Service, Research Insight Knowledge Base |
| 14 | Document Evidence Pipeline | Core | Release Follow-Up | In Review | design/cdd/document-evidence-pipeline.md | Market Data Storage, Research Insight Knowledge Base, Research Copilot Agent Runtime |
| 15 | SDK And Daemon Client Interfaces | Interface | Release Follow-Up | In Review | design/cdd/sdk-daemon-client-interfaces.md | Research Copilot Agent Runtime, FastAPI Service, Vue Web Console |

---

## Categories

| Category | Description | Typical Modules |
|----------|-------------|-----------------|
| **Foundation** | Infrastructure and primitives other modules depend on | Runtime configuration, storage, data sources |
| **Core** | Modules required for the central market-analysis workflow | Macro strategy, micro momentum, research knowledge base |
| **Feature** | User-facing analytical workflows built on core modules | Market reporting |
| **Interface** | External access surfaces and protocols | MCP server, FastAPI service, SDK/daemon clients |
| **Presentation** | Human operator UI surfaces | PyQt dashboard, Vue web console |
| **Operations** | Architecture, quality, release, and migration control | Clean architecture migration |

---

## Priority Tiers

| Tier | Definition | Target Milestone | Design Urgency |
|------|------------|------------------|----------------|
| **MVP** | Required for current local-first workflow to function | Brownfield stabilization | Design first |
| **Vertical Slice** | Required for a complete operator path across analysis and UI | Modularized v1 slice | Design second |
| **Alpha** | Expanded surface area and workflow polish | Alpha product consolidation | Design third |
| **Release Follow-Up** | Implemented post-release slices that must remain experimental until gates pass | Release hardening | Reverse-document and govern |
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
4. Research Copilot Agent Runtime — depends on persisted runtime state, tool schemas, local files, and approval/event semantics.
5. Document Evidence Pipeline — depends on persisted documents/pages/chunks/evidence and provides grounded context to the runtime.

### Feature Layer

1. Market Reporting — depends on storage analytical views (Module #2) and runtime config (Module #1); writes ticker names to the `stock_names` table shared with Module #7. It is pure SQL report generation with **no LLM** — the project's LLM lives in Module #4 and the LLM-based industry-chain clustering lives in Module #5.

### Interface Layer

1. MCP Server — exposes local tools for AI clients.
2. FastAPI Service — exposes HTTP API for web and other clients.
3. SDK And Daemon Client Interfaces — exposes Level 2/3 daemon, Python SDK, TypeScript SDK, and streaming client contracts.

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
| 9 | Market Reporting | Vertical Slice | Feature | python-specialist, security-engineer | M |
| 10 | FastAPI Service | Vertical Slice | Interface | python-specialist | M |
| 11 | PyQt Desktop Dashboard | Vertical Slice | Presentation | ui-programmer, python-specialist | M |
| 12 | Vue Web Console | Alpha | Presentation | typescript-specialist, ui-programmer | M |
| 13 | Research Copilot Agent Runtime | Release Follow-Up | Core | python-specialist, lead-programmer | M |
| 14 | Document Evidence Pipeline | Release Follow-Up | Core | python-specialist, qa-lead | M |
| 15 | SDK And Daemon Client Interfaces | Release Follow-Up | Interface | python-specialist, typescript-specialist | M |

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
| Micro Momentum Scanner | Technical/Product | The LLM-based industry-chain clustering (`src/micro/industry_analyzer.py`, Module #5) can hallucinate market/sector claims. | Keep ticker metadata calibration via `yfinance` + local JSON cache, RSRS-based trend confirmation, source grounding, retries, and cached fallback behavior. (Risk relocated from the former "AI Industry Analysis" row — that module was renamed to Market Reporting and has no LLM.) |
| Vue Web Console | Scope | Web UI expands product surface while backend migration is unfinished. | Keep web API contracts narrow until services stabilize. |
| Research Copilot Agent Runtime | Runtime/Product | Level 1/2/3 slices exist, but runtime maturity explicitly remains non-production until required gates are evidenced. | Keep `docs/progress/runtime-maturity.yaml` as the maturity source and forbid promotion claims while `production_ready: false`. |
| Document Evidence Pipeline | Data Quality | Uploaded documents, OCR/page extraction, chunking, and evidence citation can drift from source files if metadata is incomplete. | Persist document/page/chunk/evidence metadata and require source-backed retrieval tests. |
| SDK And Daemon Client Interfaces | Contract | SDK and daemon streaming clients can create a public contract before the runtime is ready. | Mark SDK daemon clients experimental until Level 2/3 gates and remote CI evidence pass. |

---

## Progress Tracker

| Metric | Count |
|--------|-------|
| Total modules identified | 15 |
| Design docs started | 15 |
| Design docs reviewed | 12 |
| Design docs approved | 0 |
| MVP modules designed | 8/8 |
| Vertical Slice modules designed | 3/3 |
| Release Follow-Up modules in review | 3/3 |

---

## Next Steps

- [ ] Review and approve this 15-module enumeration.
- [ ] Review the three Release Follow-Up CDDs (#13/#14/#15) before any runtime maturity promotion.
- [ ] Run `/design-review` on each completed CDD.
- [ ] Run `/architecture-review` after ADR and CDD coverage exists.
- [ ] Run `/sprint-plan update` after sprint scope is confirmed.
