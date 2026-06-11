# MY-DOGE-MICRO Current State

> **Generated**: 2026-06-11
> **Source repository**: `D:\Users\WSMAN\Desktop\Coding Task\MY-DOGE-MICRO`
> **Primary sources read**: `README.md`, `docs/MODULARIZATION_PLAN.md`, `docs/MCP_SERVER.md`, `pyproject.toml`, `requirements.txt`, source tree and test tree.

## Product Summary

MY-DOGE QUANT SYSTEM is a local-first quantitative investment decision-support platform. It combines local TDX data ingestion, macro market strategy generation, micro momentum scanning, LLM-assisted industry analysis, and a research insight knowledge base.

The product promise is institutional-style decision support for an individual operator while preserving local data control. The system emphasizes SQLite/DuckDB local storage, quantitative risk signals, report generation, and human-readable analysis workflows.

## Current Architecture

The README describes a three-layer architecture:

| Layer | Current Responsibilities |
|-------|--------------------------|
| Interface Layer | Dashboard, scanner, archive/data editor, insight views, analysis UI |
| Micro Layer | TDX loading, market scanning, momentum ranking, industry analysis |
| Macro Layer | Global asset data, RSRS/VolSkew calculations, DeepSeek/OpenAI-compatible strategy generation |

The active modularization plan targets Clean Architecture plus Ports & Adapters:

```text
interfaces -> application -> core/services -> core/ports <- infrastructure
```

## Implemented or In-Progress Areas

| Area | Evidence | State |
|------|----------|-------|
| Legacy micro/macro system | Tracked `src/micro`, `src/macro`, `src/interface` | Implemented baseline |
| MCP server | Untracked `mcp_server.py`, `doge_mcp.py`, `docs/MCP_SERVER.md`, startup scripts | In Progress |
| FastAPI service | Untracked `src/api/main.py` and routers | In Progress |
| Clean architecture package | Untracked `src/doge/config`, `core`, `infrastructure`, `interfaces/mcp` | In Progress |
| Vue web console | Untracked `web/` Vue/Vite app | In Progress |
| Pytest suite | Untracked `tests/test_database.py`, `tests/test_mcp_tools.py`, `tests/test_transport.py` | In Progress |
| AI analysis/reporting | Untracked `src/ai_analysis`, `ai_report/*.md` | In Progress |

## Modularization Plan Status

The source `docs/MODULARIZATION_PLAN.md` defines six migration batches:

| Batch | Target | Imported State |
|-------|--------|----------------|
| 1 | `pyproject.toml`, centralized config, remove scattered path hacks | Partially done. `pyproject.toml` and `src/doge/config/settings.py` exist, but legacy files still contain `sys.path.insert` and repeated root calculations. |
| 2 | Repository and database abstraction | In progress. `core/ports/repository.py`, DuckDB/SQLite adapters, and repositories exist under untracked `src/doge/`. |
| 3 | TDX data source abstraction | In progress. `core/ports/data_source.py` and `infrastructure/data_source/tdx.py` exist. |
| 4 | Business service layer | In progress. `core/services/*` exists for stock, ranking, breadth, anomaly, and view services. |
| 5 | Interface layer refactor | In progress. New MCP package exists, while legacy root `mcp_server.py`, `src/cli.py`, and `src/api/routers/*` still coexist. |
| 6 | Cleanup and tests | Started. Tests exist, but old compatibility code and direct DB/path coupling remain. |

## Known Architecture Debts

- Legacy code still contains scattered `sys.path.insert` usage.
- Several API/router and analysis paths still compute `_PROJECT_ROOT` locally.
- Interface/API layers still directly import or open SQLite/DuckDB in several places.
- `src/ai_analysis/__init__.py` still owns connection helpers that the new infrastructure layer is intended to replace.
- New clean architecture files are mostly untracked in Git, so progress can be lost or misread unless explicitly captured.

## Testing Evidence Imported

The source repository includes an untracked pytest suite:

```text
tests/conftest.py
tests/test_database.py
tests/test_mcp_tools.py
tests/test_transport.py
```

Test focus areas:

- MCP server validation helpers
- MCP tool formatting and input validation
- Transport/lifecycle behavior
- Database behavior

No test results were imported into this document. Verification should be run from the source repository and recorded separately if needed.

## CDD Interpretation

- Project phase: Implementation / Brownfield Modularization
- Primary CDD risk: the implemented system is ahead of formal design artifacts.
- Immediate governance need: preserve current facts, create a module index, record the clean architecture migration ADR, and then retrofit module-specific CDDs before generating new implementation stories.
