# Legacy Macro/Micro Architecture Notes

This archive preserves the former README architecture narrative for historical
reference only. The current counted architecture is the eight bounded-context
model accepted by ADR-0021 and summarized in
[../../architecture/overview.md](../../architecture/overview.md).

## Historical Narrative

The old product entry described MY-DOGE as a three-layer local quant system:

- local TDX/yfinance market-data ingestion and storage;
- Macro Beta strategy generation using an OpenAI-compatible DeepSeek client;
- Micro Alpha momentum and anomaly scanning;
- PyQt, FastAPI/Web, CLI, and MCP access surfaces;
- local SQLite persistence with DuckDB analytical reads.

That narrative helped bootstrap the brownfield project, but it mixed product
domains, delivery channels, adapters, and migration programs at the same level.

## Superseded By

- ADR-0021: eight bounded contexts are the canonical counted modules.
- ADR-0022: facade-first target source layout and compatibility migration.
- `design/cdd/module-index.md`: former 20 mixed modules are preserved as an
  appendix rather than treated as current counted modules.

## What Remains Valid

- DeepSeek/OpenAI-compatible model access still exists as a provider-backed
  implementation detail for approved LLM paths.
- Macro and industry research workflows still exist inside the Research
  bounded context.
- Momentum, breadth, anomaly, and market-reporting capabilities still exist
  inside Market Intelligence.
- SQLite and DuckDB remain local data technologies, but they are adapters and
  storage/read engines rather than product modules.

## What Is No Longer Current

- The product is not described as "Macro/Micro three-layer architecture" in
  current entry docs.
- Delivery channels such as API, Web, CLI, MCP, SDK, and PyQt are not counted
  product modules.
- Adapter/provider choices such as SQLite, DuckDB, TDX, yfinance, Kimi,
  DeepSeek, and akshare are not counted product modules.
- Production or Stable maturity may not be claimed while
  `docs/progress/runtime-maturity.yaml` keeps `production_ready: false` and
  `stable_declaration: forbidden`.
