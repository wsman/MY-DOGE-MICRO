# Bounded Context 01: Market Intelligence

> **Status**: In Review
> **Author**: Codex
> **Last Updated**: 2026-06-23
> **Related ADRs**: ADR-0001, ADR-0003, ADR-0004, ADR-0021
> **Source Baseline**: docs/progress/platformization-consolidation-baseline.md

## Overview

Market Intelligence owns market-facing analytical capabilities that help an
operator understand current price, volume, breadth, trend, and watchlist state.
It is a product bounded context, not an API surface or storage adapter.

## User Promise

An operator can scan markets, inspect momentum, detect unusual activity, and
produce market reports without needing to know which data adapter or entrypoint
served the data.

## Responsibilities

- Own stock quote, OHLCV, market scan, and watchlist product semantics.
- Own RSRS, breadth, volume anomaly, and scanner result contracts.
- Own market report assembly and market-specific result explanations.
- Define product-level ports for market data and market metadata.
- Publish capabilities that can be discovered through the Capability Registry.

## Out of Scope

- Does not own SQLite, DuckDB, TDX, yfinance, akshare, or provider clients.
- Does not own FastAPI, Web, MCP, CLI, SDK, or PyQt delivery surfaces.
- Does not own research-case organization, runtime execution, evidence
  retrieval, ACL, audit, approval, or budget policy.

## Public Contract

| Contract | Shape | Consumers |
|----------|-------|-----------|
| Market scan capability | Request filter -> ranked result set | Web, API, SDK, workflows |
| RSRS capability | Symbol universe + window parameters -> trend ranks | Market workflows, reports |
| Breadth capability | Market/date range -> advance/decline metrics | Home dashboard, reports |
| Volume anomaly capability | Universe/date range -> abnormal volume ranks | Market workflows |
| Watchlist capability | Watchlist CRUD and membership queries | Web, SDK, templates |

## Current Source Surfaces

| Existing Artifact | Treatment |
|-------------------|-----------|
| `design/cdd/micro-momentum-scanner.md` | Preserved as detailed design input for scanners. |
| `design/cdd/market-reporting.md` | Preserved as detailed design input for reports. |
| `design/cdd/data-sources.md` | Reclassified as market-data adapter guidance. |
| `design/cdd/market-data-storage.md` | Reclassified as persistence adapter guidance. |
| Market tool providers | Move toward `products/market` during provider migration. |

## Dependencies

- Depends on market-data adapters for external data retrieval.
- Depends on persistence adapters for cached market state and reports.
- Exposes capabilities to Workspace & Workflow and Agent Runtime through ports.
- May consume Knowledge & Evidence only through explicit evidence ports when a
  market report includes sourced claims.
- Must not directly import other product bounded contexts.

## Migration Acceptance Criteria

- Market product services are reachable through a stable public contract.
- Current scanner and reporting tests still pass through compatibility exports.
- Data-source and persistence details are not counted as Market modules.
- Market capabilities appear in the Capability Registry without secrets.
- Adding a new market data provider requires an adapter, not product-service
  rewrites.

## Governance Notes

- Production readiness remains blocked by `docs/progress/runtime-maturity.yaml`.
- Financial provider approval gates still apply to live or paid data sources.
- Tool entitlement and high-risk action handling remain owned by Governance &
  Evaluation.
