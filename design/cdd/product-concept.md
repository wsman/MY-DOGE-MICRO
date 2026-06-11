# Product Concept Document: MY-DOGE QUANT SYSTEM

> **Source**: Metadata import from `D:\Users\WSMAN\Desktop\Coding Task\MY-DOGE-MICRO`
> **Created**: 2026-06-11
> **Last updated**: 2026-06-11
> **Status**: In Design

## Core Identity

| Field | Value |
|-------|-------|
| **Working Title** | MY-DOGE QUANT SYSTEM |
| **Elevator Pitch** | A local-first quantitative investment command platform that combines TDX data ingestion, macro strategy, micro momentum scanning, and LLM-assisted industry research for personal investors. |
| **Core Action** | Run a market scan or analysis workflow, then inspect generated rankings, reports, and archived insights. |
| **Core Promise** | Give an individual operator a disciplined, local, data-backed view of market risk and opportunity. |
| **Unique Hook** | Like a personal quant terminal, and also a local research memory that blends quantitative signals with AI-calibrated industry reasoning. |
| **Primary User Need** | Make better market decisions without surrendering data control or stitching together many manual tools. |
| **Estimated Scope** | Large solo/small-team product; existing implementation is already in progress. |

## Discovery Brief

The imported source project shows an active local-first quant system rather than a fresh concept. The product is shaped around an operator who wants TDX data cleaning, A-share and US market scanning, macro risk framing, LLM-assisted industry analysis, and historical research recall in one workflow. The strongest constraints are local data ownership, reliability under imperfect network conditions, and preventing model hallucination through market-data calibration. The current implementation has outpaced the CDD artifact set, so this concept anchors future governance rather than starting ideation from zero.

## User Journey

### Micro-Interaction (seconds)

The user opens the dashboard, chooses a market or analysis action, and starts a scan, lookup, or report-generation task.

### Task Completion (minutes)

The user waits for data loading, filtering, ranking, report generation, or MCP/API responses, then reviews tables, generated reports, and insight summaries.

### Workflow (hours)

A complete session can include refreshing local market data, running macro strategy analysis, scanning momentum candidates, generating an industry report, and archiving conclusions for later comparison.

### Relationship (days/weeks/months)

The product becomes more valuable as local databases, cached ticker metadata, user notes, and generated research reports accumulate into a personal market memory.

### User Motivation Analysis (Self-Determination Theory)

| Dimension | Assessment |
|-----------|------------|
| **Autonomy** | High. Local storage, configurable models, CLI/API/MCP/GUI surfaces, and editable data give the user control over workflow and data. |
| **Competence** | High. Rankings, indicators, reports, and historical notes help the user build a repeatable analysis discipline. |
| **Relatedness** | Medium. The main relationship is between the user and their research corpus; MCP integration also lets AI assistants participate in the workflow. |

## Principles

### Product Principles

| # | Principle | Definition | Design Test |
|---|-----------|------------|-------------|
| 1 | Local First | Market data, reports, notes, and configuration should remain usable without cloud dependency. | If a feature requires cloud state, it must still degrade to local inspection or cached output. |
| 2 | Evidence Before Narrative | AI-generated conclusions must be grounded in market data, ticker metadata, or explicit user-provided context. | If the model makes a claim, the workflow should show or preserve the evidence path. |
| 3 | Operator Control | Long-running scans and model calls should be visible, cancellable where feasible, and recoverable. | If a task may take time or fail, the user needs status and a useful fallback. |
| 4 | Layered Interfaces | GUI, web, CLI, API, and MCP should share domain services rather than fork business rules. | If two surfaces expose the same action, they should route through the same service contract. |
| 5 | Incremental Migration | Existing working flows should keep functioning while architecture is cleaned up. | If a refactor breaks a user workflow, it must ship with a compatibility path or staged rollout. |

### Anti-Principles

| # | What we will NOT do | Because it would compromise |
|---|---------------------|----------------------------|
| 1 | Move user market databases to a remote required service | Local First |
| 2 | Let AI analysis bypass ticker validation and market-data grounding | Evidence Before Narrative |
| 3 | Duplicate core business logic separately in GUI, API, CLI, and MCP | Layered Interfaces |
| 4 | Rewrite all legacy modules in one unverified step | Incremental Migration |

## Visual Identity Anchor

- **Visual direction:** Analytical command console
- **One-line visual rule:** Dense but legible market intelligence, with status and evidence always close to the decision.
- **Supporting visual principles:**
  1. Prioritize scanability for tables, reports, and status.
  2. Use restrained visual hierarchy for repeated daily workflows.
  3. Keep generated reports readable as durable research artifacts.
- **Design philosophy summary:** The product should feel like a workbench for repeated market analysis, not a marketing dashboard. Visual polish should improve orientation, comparison, and confidence.

## Target Users

### Primary User

A technically comfortable personal investor or solo quant operator who maintains local market data and wants structured support for daily or weekly market analysis.

**Job they're hiring for (JTBD):**
"When I need to decide where risk and opportunity are concentrated, I want to run a repeatable local scan and AI-assisted analysis, so I can act from evidence instead of scattered notes and intuition."

### Secondary Users

- AI-assisted coding or research workflows that query the local market database through MCP.
- Developers extending the platform with new indicators, data adapters, report types, or UI surfaces.

### Who This Is NOT For

- Users seeking fully managed cloud brokerage automation.
- Users unwilling to maintain local data files, model configuration, or Python dependencies.
- Teams requiring regulated investment-advice compliance out of the box.

### Market Validation

- Successful adjacent products include retail quant terminals, local data analysis notebooks, trading dashboards, and AI research copilots.
- Users often complain about fragmented data sources, hallucinated AI market claims, expensive terminals, and brittle local scripts.
- The switching trigger is the desire for one local workflow that joins data ingestion, indicators, reports, and AI-assisted interpretation.

## Scope

### Target Platform

Local Windows-first desktop/server workflow with CLI, PyQt desktop UI, FastAPI HTTP API, MCP client integration, and Vue/Vite web UI.

### Tech Stack

Python 3.10+, FastAPI, MCP, PyQt6, SQLite, DuckDB, pandas/scipy, yfinance, TDX/opentdx, akshare, OpenAI-compatible model clients, Vue 3, Vite, TypeScript.

### Feature Scope (MVP)

- Local market database ingestion and inspection.
- Stock lookup, ranking, market breadth, and anomaly MCP tools.
- Macro and micro scan workflows.
- Report archive and insight lookup.
- Basic UI/API access to core workflows.

### Feature Scope (Full Vision)

- Clean architecture services shared by CLI, API, MCP, desktop, and web.
- Robust market data adapters with caching and retry behavior.
- Rich web console for scan orchestration, charting, reports, and notes.
- Regression-tested migration away from legacy path and DB coupling.

### Scope Tiers

| Tier | What's included | Ships when |
|------|-----------------|------------|
| MVP | Existing local scans, MCP tools, database access, and report generation stabilized | Current brownfield implementation |
| v1 | Clean architecture migration, tested shared services, stable API/MCP/Web/Desktop surfaces | After modularization batches complete |
| v2+ | Advanced portfolio workflows, richer analytics, stronger observability, broader data-source support | Post-v1 expansion |

## Risks

| Category | Risk | Severity | Mitigation |
|----------|------|----------|------------|
| Technical | Legacy modules still use path hacks and direct DB access. | High | Migrate behind centralized settings, ports, repositories, and shared services. |
| Technical | External market and model APIs can fail, change, or rate-limit. | High | Keep caching, retries, degraded offline behavior, and explicit error states. |
| Design | Multiple interfaces can drift in behavior. | Medium | Route CLI/API/MCP/GUI/Web through common services. |
| Data | Local databases may become inconsistent or too large for naive UI reads. | Medium | Use repository boundaries, DuckDB analytical views, and bounded UI queries. |
| Adoption | Users may not trust AI-generated market analysis. | Medium | Preserve evidence, ticker calibration, and source report context. |

## Next Steps

1. Review `design/cdd/module-index.md`.
2. Author CDDs for the highest-risk modules: Clean Architecture Migration, Market Data Storage, MCP Server, FastAPI Service.
3. Run `/architecture-review` after ADR and module CDDs exist.
4. Run `/create-control-manifest` after ADRs are accepted.
5. Run `/sprint-plan update` to create machine-readable sprint status.
