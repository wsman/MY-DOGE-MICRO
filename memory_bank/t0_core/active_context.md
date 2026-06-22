# Active Context

## Repo Status

- Project: MY-DOGE QUANT SYSTEM
- Current working state: Release follow-up with active runtime, evidence, SDK, RAG, industry-report, and release-quality hardening work.
- Current HEAD: `9b77f9cb87a59cb1bd4a0ce39d5cf5687e066d5b` (Kimi enterprise model gateway, tool governance, tenant context, multimodal evidence, SDK/CLI/Kimi agent backend extensions).
- Layer model: T0 (laws) -> T1 (support) -> T2 (execution) -> T3 (archive)
- Domain: Product
- Review mode: lean (`production/review-mode.txt`)
- Stage source: `production/stage.txt`

## Core Thesis

MY-DOGE is a local-first quantitative investment command platform for a personal operator who wants repeatable, data-backed market scans, reports, evidence recall, and AI-assisted research without surrendering local data control.

**Anti-thesis:** MY-DOGE is not a cloud-required brokerage automation product, not regulated investment advice, not an ungrounded AI narrator, and not a rewrite-first migration.

## Constitution Version

- Version: 1.0
- Last amended: 2026-06-21
- Last sign-off: 2026-06-21 by operator approval in Codex `/constitute`
- Source basis: `design/cdd/product-concept.md`, `design/cdd/module-index.md`, 16 CDD files, 14 Accepted ADRs, `docs/architecture/architecture-traceability.md`, `docs/progress/runtime-maturity.yaml`, and production sprint/release evidence.

## Active Decisions

- Local-first posture: accepted. SQLite/DuckDB/local documents remain the persistence baseline.
- Runtime maturity: accepted as level-labeled but not production-ready; `docs/progress/runtime-maturity.yaml` is authoritative.
- API/CORS posture: loopback-guaranteed posture accepted; non-loopback exposure requires auth and explicit CORS hardening first.
- Architecture migration: incremental clean-architecture migration remains binding; compatibility shims and legacy debt are governed by ADR/CDD evidence.
- Review mode: lean, with strict QA for contract/API/governance gates.

## Active Risks

- Runtime Stable promotion is forbidden while `production_ready: false`.
- Live Kimi file/vision smoke, citation-quality evaluation, browser/manual SSE reconnect evidence, RAG quality benchmarking, real fundamentals/connectors, legacy TDX helper deletion, and executed soak evidence remain open.
- Legacy API/CLI/GUI surfaces may still carry migration debt and must not gain new direct DB or path-coupling patterns.
- Financial and AI-assisted outputs must keep evidence/citation quality explicit to avoid unsupported market claims.

## Module Status

| Module | Release status | Evidence status | Open risks |
|--------|----------------|-----------------|------------|
| Runtime Configuration | released foundation | current | config drift must stay behind settings |
| Market Data Storage | released foundation | current | local DB consistency and bounded reads |
| TDX/YFinance Data Sources | released foundation | partial live evidence | live TDX/yfinance availability varies |
| Macro Strategy Engine | released core | current | provider failures must degrade cleanly |
| Micro Momentum Scanner | released core | current | RSRS/view consistency remains governed |
| Market Reporting | released feature | current | pure SQL boundary must stay no-LLM |
| Research Insight Knowledge Base | released core | current | notes/evidence retention boundaries |
| MCP Server | released interface | current | transport and tool contracts must remain stable |
| FastAPI Service | release follow-up interface | current | route/docs parity and loopback posture |
| PyQt Desktop Dashboard | vertical-slice presentation | partial | GUI evidence remains mostly smoke/manual |
| Vue Web Console | alpha presentation | current | browser/manual reconnect evidence pending |
| Clean Architecture Migration | ongoing operations | current | legacy debt deletion remains incremental |
| Research Copilot Agent Runtime | release follow-up core | current but not production-ready | maturity gates remain blocking for Stable |
| Document Evidence Pipeline | release follow-up core | partial live evidence | citation quality and live Kimi smoke pending |
| SDK And Daemon Client Interfaces | experimental interface | current | packaging/distribution hardening pending |

## Constitution Changelog

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-06-21 | Operator + Codex | Initial constitution derived from existing Product CDDs, ADRs, control manifest, production sprint/release evidence, and runtime maturity registry. |
