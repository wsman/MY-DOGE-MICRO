# Python Product Stack Version Reference

> **Generated**: 2026-06-11
> **Source**: Imported from `D:\Users\WSMAN\Desktop\Coding Task\MY-DOGE-MICRO\pyproject.toml` and `requirements.txt`
> **Scope**: Local-first OpenDoge product stack
> **Latest-version claim**: None. This file records the source repository's pinned/imported versions, not the latest upstream releases.

## Runtime

| Component | Version / Constraint | Role |
|-----------|----------------------|------|
| Python | `>=3.10` | Primary backend, CLI, MCP, data pipeline language |
| TypeScript | `~6.0.2` | Web UI language |
| Node/Vite toolchain | Vite `8.0.10` | Web UI build and dev server |

## Backend and Product Libraries

| Package | Version | Role |
|---------|---------|------|
| FastAPI | `0.123.8` | HTTP API |
| Uvicorn | `0.38.0` | ASGI server |
| Pydantic | `2.12.4` | Validation and schemas |
| MCP | `1.25.0` | Model Context Protocol server |
| sse-starlette | `3.0.3` | SSE transport |
| httpx | `0.28.1` | HTTP client/testing support |
| OpenAI SDK | `1.62.0` | OpenAI-compatible model clients |

## Data and Market Libraries

| Package | Version / Constraint | Role |
|---------|----------------------|------|
| DuckDB | `1.4.4` | Analytical views over local data |
| pandas | `2.2.3` | DataFrame processing |
| scipy | `1.16.3` | Quantitative calculations |
| yfinance | `0.2.66` | Market data lookup |
| opentdx | unpinned | TDX data access |
| akshare | unpinned | China market data support |

## UI and Testing

| Package | Version / Constraint | Role |
|---------|----------------------|------|
| pytest | `9.0.1` | Python tests |
| pytest-asyncio | `1.3.0` | Async tests |
| Vue | `3.5.32` | Web UI |
| Pinia | `3.0.4` | Web UI state |
| Naive UI | `2.44.1` | Web UI components |

## Verification Notes

- Treat unpinned dependencies (`opentdx`, `akshare`) as upgrade-risk items until pinned.
- ADRs should cite this file when making decisions that depend on imported stack versions.
- If the source repository changes `pyproject.toml`, `requirements.txt`, or `web/package.json`, refresh this file before architecture review.
