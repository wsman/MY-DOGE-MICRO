# Tech Context

## Technology Stack

| Layer | Choice | Version | Rationale |
|-------|--------|---------|-----------|
| Primary language | Python | 3.10+ | Backend/domain tooling, MCP, data adapters, local services |
| Secondary language | TypeScript | project web toolchain | Vue/Vite web UI and TypeScript SDK |
| Backend/API | FastAPI, Uvicorn, Pydantic | FastAPI 0.123.8, Uvicorn 0.38.0, Pydantic 2.12.4 | Loopback HTTP API and daemon/v1 routes |
| MCP | mcp | 1.25.0 | stdio and SSE AI-client integration |
| Desktop UI | PyQt6 | pinned in project dependencies | Windows-first local dashboard |
| Web UI | Vue, Vite, Pinia, Naive UI | Vue 3.5.32, Vite 8.0.10, Pinia 3.0.4, Naive UI 2.44.1 | Dense local operator console |
| Data | SQLite, DuckDB | DuckDB 1.4.4 | Local persistence plus analytical reads/views |
| Market/AI integrations | yfinance, opentdx, akshare, OpenAI-compatible SDK | yfinance 0.2.66, OpenAI SDK 1.62.0 | Market data and provider-neutral model clients |

## Technology Decision Record

- Selected stack: Python local backend/domain tooling plus TypeScript Vue/Vite presentation and SDK clients.
- Version source: `standards/technical-preferences.md`, `requirements.txt`, `pyproject.toml`, `web/package.json`, `docs/reference/python/VERSION.md`.
- Reason chosen: supports local-first Windows workflows, MCP/API/CLI/Desktop/Web surfaces, local data ownership, and incremental clean-architecture migration.
- Alternatives rejected: cloud-required database/service control plane; duplicated business logic per interface; rewrite-first migration.
- Compatibility constraints: Windows paths are first-class; network/provider calls must degrade; loopback binding is a security assumption; runtime maturity labels must not be inflated.
- Knowledge risk: MEDIUM because provider APIs, SDK streaming semantics, Vite/Vue versions, and market data integrations can change.
- Last verified date: 2026-06-21.

## Performance Budgets

| Metric | Target | Measurement |
|--------|--------|-------------|
| MCP local tool latency | Common queries under 30 seconds | MCP timeout and transport tests |
| Local database reads | bounded UI/API reads, DuckDB analytical reads for cross-db views | repository/view tests and performance smoke |
| Long-running scans/model calls | visible progress, cancellation/retry/degraded state | API/SSE, CLI, worker, and web tests |
| Release-quality smoke | sprint-specific performance tests pass | `tests/performance/test_sprint_015_release_gates.py` |

## External Dependencies

| Dependency | Purpose | Risk if unavailable |
|------------|---------|---------------------|
| yfinance | market data and metadata | degraded market refresh; use caching/fallback |
| opentdx / TDX | A-share local/remote data ingestion | environment-dependent live smoke |
| akshare | optional market data integration | connector availability can drift |
| OpenAI-compatible providers / Kimi / DeepSeek | LLM, file, vision, and research workflows | live provider smoke and rate-limit behavior must be explicit |
| Node/npm | web and TypeScript SDK tests/builds | local build verification required |

## Forbidden Patterns

- `sys.path.insert` bootstrapping outside compatibility shims.
- Repeated project-root path calculation outside centralized settings.
- Interface/API layers directly opening SQLite or DuckDB connections.
- Cross-layer imports that bypass ports/services.
- Network-dependent tests without isolation, fixtures, or explicit integration markers.
