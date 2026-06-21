# System Patterns

## Architectural Style

- Primary style: incremental Clean Architecture for a brownfield local-first product.
- Dependency direction: interfaces -> application/core services -> ports <- infrastructure adapters.
- Rationale: supports BL-02 Local First, BL-05 Layered Interfaces, and BL-06 Incremental Migration.
- Canonical control source: `docs/architecture/control-manifest.md`.

## Module Boundaries

| Module | Responsibility | Owns | Communicates via |
|--------|----------------|------|------------------|
| Runtime Configuration | settings, paths, env defaults | `Settings`, local paths, runtime knobs | `get_settings()` |
| Market Data Storage | local persistence and analytical views | SQLite DBs, DuckDB views, repositories | repository ports |
| TDX/YFinance Data Sources | market data adapters | source adapters and normalization | `IMarketDataSource`, metadata ports |
| Macro Strategy Engine | macro reporting and model-assisted framing | strategy workflow, provider failure handling | services and LLM port/adapter |
| Micro Momentum Scanner | RSRS, breadth, anomaly, ranking workflows | scanner algorithms and view-backed reads | use cases/services |
| Market Reporting | SQL-based local reports | Markdown/JSON market artifacts | report services |
| Research Insight Knowledge Base | notes, insight lookup, local research memory | notes and research DB | note/evidence/retrieval ports |
| MCP Server | AI-client tool surface | read-only local tools | MCP stdio/SSE transports |
| FastAPI Service | local HTTP and daemon API | route contracts and v1 runtime endpoints | FastAPI routers/dependencies |
| PyQt Desktop Dashboard | desktop operator workflow | GUI orchestration | services/use cases |
| Vue Web Console | browser operator workflow | web client state and views | API/SDK/SSE |
| Clean Architecture Migration | migration rules and gates | layer contract, forbidden patterns | ADR/CDD/control manifest |
| Research Copilot Agent Runtime | session/run/turn/event/tool/model runtime | durable runtime state and event flow | daemon/CLI/services |
| Document Evidence Pipeline | upload/page/chunk/evidence/citation base | document and evidence metadata | repositories/RAG/context builder |
| SDK And Daemon Client Interfaces | Python/TypeScript/web client contracts | SDK streaming and daemon clients | `/v1/*`, SSE, SDK APIs |

## Data Ownership Rules

- Local market and research data remain local by default.
- SQLite persists local state; DuckDB is used for analytical reads/views.
- Interfaces do not open DB drivers directly; they call services/use cases.
- External provider IDs and request shapes may be metadata, but canonical evidence remains local.
- Generated reports and claims must preserve evidence/citation paths when available.

## Pattern Notes

- ADR-0001 governs the migration pattern.
- ADR-0002 governs runtime configuration.
- ADR-0003/0004/0009/0010 govern storage, data source, cache/metadata, and view-service ports.
- ADR-0006/0007/0008 govern MCP/API/Web surfaces.
- ADR-0011 governs runtime levels and maturity labels.
