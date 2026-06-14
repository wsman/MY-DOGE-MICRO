# CDD: MCP Server (Module #8)

> **Module #8** - Category: **Interface**
> **Slug**: `mcp-server`
> **Status**: Reverse-documented, Wave 4 updated - 2026-06-12
> **Depends on**: #1 `runtime-configuration`, #2 `market-data-storage`, #7 `research-insight-knowledge-base`
> **Depended on by**: Claude Code / MCP clients, optional local SSE clients
> **Source files reverse-documented**: `doge_mcp.py`, `src/doge/interfaces/mcp/server.py`, `src/doge/interfaces/mcp/tools/*.py`, `docs/MCP_SERVER.md`, `.mcp.json`, `scripts/mcp_stdio.bat`, `scripts/start_mcp_sse.{sh,bat}`
> **Related ADRs**: [ADR-0006](../../docs/architecture/adr-0006-mcp-transport-strategy.md), [ADR-0003](../../docs/architecture/adr-0003-storage-repository-contract.md), [ADR-0001](../../docs/architecture/adr-0001-brownfield-clean-architecture.md)

---

## 1. Overview

The MCP Server (`doge-db`) is the AI-facing analytical interface of
MY-DOGE-MICRO. It exposes exactly six read-only tools over two transports:
stdio for Claude Code and SSE for local HTTP MCP clients. Wave 4 retired the
legacy root monolith; `doge_mcp.py` is now the canonical repo-root entrypoint
and delegates to `src/doge/interfaces/mcp/server.py`.

All tool implementations live under `src/doge/interfaces/mcp/tools/` and route
through `doge.core.services`. Analytical reads use the storage layer's DuckDB
read model and repository adapters; the tool boundary handles validation,
timeouts, and string formatting for MCP clients.

## 2. User Promise / JTBD

**Operator JTBD**: "From Claude Code, ask for local market data, trend ranks,
market breadth, abnormal volume, and available DuckDB views without opening the
desktop app or writing SQL."

The module must:

- Start from `.mcp.json` through `scripts/mcp_stdio.bat` with no manual Python
  path edits.
- Also support SSE mode on loopback `127.0.0.1:8902`.
- Return strings for every tool result; exceptions and timeouts become
  `"Error: ..."` strings, never uncaught MCP transport errors.
- Enforce `TOOL_TIMEOUT = 30` for each tool call.
- Keep all six tools read-only.

The module does not:

- Own the DuckDB view definitions or SQLite schemas.
- Own FastAPI routes; the web/API surface is Module #9.
- Write price data, notes, reports, or configuration.

## 3. Detailed Behavior

### 3.1 Entry points and transports

| Transport | Purpose | Launch | Registered path |
|---|---|---|---|
| stdio | Claude Code local MCP integration | `python doge_mcp.py --transport stdio` | `.mcp.json` -> `scripts/mcp_stdio.bat` |
| SSE | Local HTTP MCP clients / liveness probes | `python doge_mcp.py --transport sse --host 127.0.0.1 --port 8902` | `scripts/start_mcp_sse.{sh,bat}` |

`doge_mcp.py` contains no `sys.path` shim. The project must be importable via
the package/editable-install layout (`pyproject.toml` + `src/` package roots).

### 3.2 Server lifecycle, logging, and PID tracking

`src/doge/interfaces/mcp/server.py` configures:

- `logs/mcp_server.log` with a rotating file handler. The filename is retained
  for operational compatibility even though the monolith was deleted.
- `data/.mcp_server.pid` for advisory orphan detection. Detection is read-only:
  it logs a warning for other live `doge_mcp.py` processes and never kills them.
- `correlation_id` contextvars so tool calls can be traced in logs.

### 3.3 Tool contract

Every tool:

- Is async and returns `str`.
- Is registered from `src/doge/interfaces/mcp/server.py`.
- Uses `_timed(tool_name)` so timeout and exceptions are converted to strings.
- Applies validation at the tool boundary before service calls.

Validation helpers:

- `_validate_market`: whitelist `{"cn", "us"}`.
- `_validate_ticker`: non-empty string, length bound, safe character set.
- `_validate_int`: integer bounds such as `days` and `top`.
- `_validate_float`: float bounds such as `min_ratio`.

### 3.4 Tools

| Tool | Signature | Service path | Notes |
|---|---|---|---|
| `query_stock` | `(ticker, market="cn", days=20)` | `StockService.get_history` | Returns recent OHLCV/view rows. |
| `stock_overview` | `(ticker, market="cn")` | `StockService.get_overview` | Includes notes and filters soft-deleted notes. |
| `rsrs_ranking` | `(market="cn", top=20)` | `RankingService.rsrs` | Reads RSRS DuckDB view. |
| `market_breadth` | `(market="cn", days=10)` | `BreadthService.breadth` | Reads market breadth view. |
| `volume_anomalies` | `(min_ratio=3.0, top=20)` | `AnomalyService.anomalies` | CN-only anomaly view in current implementation. |
| `list_views` | `()` | `ViewService.list_views` | Enumerates views and row counts. `run_sql` is intentionally absent. |

### 3.5 Health and metrics

SSE mode exposes:

- `GET /health`: returns `{"status":"ok"}` when the server can answer its
  health probe.
- `GET /metrics`: returns request counts and duration counters.

These routes are not available in stdio mode.

## 4. Contracts / Data Model

### 4.1 Inputs

| Input | Owner | Use |
|---|---|---|
| `MCPConfig.tool_timeout` | Module #1 | Mirrors `TOOL_TIMEOUT = 30`. |
| `MCPConfig.sse_host` / `sse_port` | Module #1 | Defaults for SSE scripts and docs. |
| DuckDB analytical views | Module #2 | Query/ranking/breadth/anomaly/list views. |
| `stock_names` / `stock_notes` | Module #7 | `stock_overview` contextual metadata and notes. |

### 4.2 Outputs

| Output | Owner | Contract |
|---|---|---|
| MCP tool result | Module #8 | Always a string. |
| MCP error result | Module #8 | `"Error: <type/message>"`, not raised. |
| MCP log line | Module #8 | Includes timestamp, level, correlation id, logger, message. |

## 5. Edge Cases

| Case | Expected behavior |
|---|---|
| Invalid market | Return `"Error: ValueError: Invalid market..."`. |
| Invalid ticker characters | Return an `"Error: ValueError..."` string before DB access. |
| Tool exceeds 30 seconds | Return `"Error: <tool> timed out after 30s"`. |
| DuckDB view errors during `list_views` | Preserve the view entry and report `rows: None` for that view. |
| Soft-deleted notes exist | `stock_overview` excludes them from MCP output. |
| Multiple MCP stdio processes remain in PID file | Log a warning only; do not kill. |

## 6. Dependencies

| Upstream module | Relationship |
|---|---|
| Runtime Configuration | Supplies MCP host/port/timeout and data paths. |
| Market Data Storage | Supplies DuckDB views and repository adapters. |
| Research Insight Knowledge Base | Supplies `stock_notes` soft-delete semantics. |
| Clean Architecture Migration | Governs no direct DB drivers in interface code. |

| Downstream consumer | Relationship |
|---|---|
| Claude Code / MCP clients | Invoke stdio tools through `.mcp.json`. |
| Local HTTP MCP clients | Invoke SSE transport on loopback. |

## 7. Configuration Knobs

| Knob | Default | Source | Risk |
|---|---|---|---|
| `--transport` | `stdio` | `doge_mcp.py` / server argparse | Low. |
| `--host` | `127.0.0.1` | server argparse + `MCP_HOST` scripts | High if changed to `0.0.0.0`. |
| `--port` | `8902` | server argparse + `MCP_PORT` scripts | Low unless port collides. |
| `--log-level` | `INFO` | server argparse | Low. |
| `TOOL_TIMEOUT` | `30` seconds | `src/doge/interfaces/mcp/server.py` | Medium if raised or lowered without budget review. |

## 8. Acceptance Criteria

- [x] `.mcp.json` and scripts launch `doge_mcp.py`.
- [x] `doge_mcp.py` has no `sys.path.insert` / `sys.path.append` fallback.
- [x] The legacy monolith is deleted after modular parity evidence.
- [x] The server registers exactly six tools with Chinese descriptions.
- [x] `run_sql` is absent.
- [x] `stock_overview` filters soft-deleted notes.
- [x] Transport tests cover stdio initialize and SSE `/health`, `/metrics`,
  and `/sse`.
- [x] Layer gate asserts no root entrypoint shim.

## 9. Open Questions / Follow-Ups

1. Should `TOOL_TIMEOUT` be read directly from `MCPConfig.tool_timeout` instead
   of mirrored as a module constant?
2. Should MCP error text be sanitized further before returning to clients?
3. Should orphan detection move from `wmic` to CIM / PowerShell on newer
   Windows versions?

*Reverse-documented 2026-06-12; Wave 4 update applied after Batch-6 monolith deletion.*
