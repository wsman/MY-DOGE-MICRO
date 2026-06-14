# Technical Preferences

<!-- Populated from the MY-DOGE-MICRO metadata import on 2026-06-11. -->
<!-- All agents reference this file for project-specific standards and conventions. -->

## Product Stack & Language

- **Domain**: Local-first quantitative investment decision-support platform
- **Primary Language**: Python 3.10+
- **Secondary Language**: TypeScript for Vue/Vite web UI
- **Backend/API Framework**: FastAPI 0.123.8, Uvicorn 0.38.0, Pydantic 2.12.4
- **MCP Framework**: mcp 1.25.0 with stdio and SSE transports
- **Desktop UI**: PyQt6
- **Web UI**: Vue 3.5.32, Vite 8.0.10, Pinia 3.0.4, Naive UI 2.44.1
- **Data Stack**: SQLite local databases and DuckDB 1.4.4 analytical views
- **Market/AI Integrations**: yfinance 0.2.66, opentdx, akshare, OpenAI SDK 1.62.0
- **Version Reference**: docs/reference/python/VERSION.md

## Input & Platform

- **Target Platforms**: Local desktop, local web browser, CLI/server process, MCP clients
- **Input Methods**: Keyboard/mouse for GUI and web UI; CLI arguments; MCP tool calls; HTTP API requests
- **Primary Input**: Local operator commands that trigger market scans, report generation, stock lookup, and data sync
- **Gamepad Support**: None
- **Touch Support**: Not targeted for current scope
- **Platform Notes**: Windows paths and local-first data directories are first-class constraints; cross-platform shell scripts exist for MCP startup.

## Naming Conventions

- **Classes**: PascalCase for Python and TypeScript classes
- **Variables**: snake_case in Python; camelCase in TypeScript
- **Signals/Events**: descriptive verb phrases for UI and transport events
- **Files**: snake_case for Python modules; PascalCase for Vue components; kebab-case acceptable for docs
- **API Routes**: resource-oriented paths under FastAPI routers
- **Constants**: UPPER_SNAKE_CASE for module constants; typed settings objects for shared configuration

## Performance Budgets

- **MCP Tool Latency**: Common local queries should return within 30 seconds, matching current MCP timeout.
- **Database Reads**: Prefer DuckDB analytical reads for cross-database views and SQLite for persisted local state.
- **UI Responsiveness**: Long-running scans and analyses must run off the UI thread or stream progress.
- **Network Calls**: External market/API lookups must tolerate retries, caching, and degraded/offline behavior.
- **Memory Ceiling**: Keep local-first workflows bounded by dataset size; avoid loading full market history into UI memory.

## Testing

- **Framework**: pytest 9.0.1, pytest-asyncio 1.3.0, Starlette/FastAPI test clients, Vue type/build checks
- **Minimum Coverage**: No numeric threshold imported yet; every new service, route, MCP tool, and data adapter must include focused tests.
- **Required Tests**: MCP validation and transport, database adapters/repositories, market data normalization, API router behavior, GUI/web smoke paths where feasible.

## Forbidden Patterns

<!-- Add patterns that should never appear in this project's codebase -->
- Scattered `sys.path.insert` bootstrapping outside compatibility shims
- Repeated project-root path calculation outside centralized settings
- Interface/API layers directly opening SQLite or DuckDB connections
- Cross-layer imports that bypass ports/services in the clean architecture target
- Network-dependent tests without isolation, fixtures, or explicit integration markers

## Allowed Libraries / Addons

<!-- Add approved third-party dependencies here -->
- duckdb, pandas, scipy, tabulate, tqdm
- yfinance, opentdx, akshare
- openai
- mcp, fastapi, uvicorn, sse-starlette, pydantic, httpx
- PyQt6
- pytest, pytest-asyncio
- Vue, Vite, Pinia, Naive UI, axios, lightweight-charts, markdown-it, highlight.js

## Architecture Decisions Log

<!-- Quick reference linking to full ADRs in docs/architecture/ -->
- [ADR-0001: Brownfield Clean Architecture Migration](../docs/architecture/adr-0001-brownfield-clean-architecture.md)

## Product Specialists

<!-- Read by /code-review, /architecture-decision, /architecture-review, and team skills -->
<!-- to know which specialist to spawn for product-specific validation. -->

- **Primary**: lead-programmer
- **Language/Code Specialist**: python-specialist
- **Frontend Specialist**: typescript-specialist
- **UI Specialist**: ui-programmer
- **Additional Specialists**: security-engineer, devops-engineer, qa-lead
- **Routing Notes**: Treat this as a product project. Route Python backend/domain/MCP work to python-specialist and Vue/Vite work to typescript-specialist or ui-programmer.

### File Extension Routing

<!-- Skills use this table to select the right specialist per file type. -->

| File Extension / Type | Specialist to Spawn |
|-----------------------|---------------------|
| `.py` backend/domain/MCP/API code | python-specialist |
| `.vue`, `.ts`, `.tsx`, web UI code | typescript-specialist |
| FastAPI route/schema files | python-specialist |
| MCP server/tool files | python-specialist |
| SQL/database adapter files | python-specialist |
| Test files | qa-lead |
| Product UX/UI screens | ui-programmer |
| General architecture review | Primary |
