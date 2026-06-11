# ADR-0006: MCP Transport Strategy

## Status

Accepted

## Date

2026-06-12

## Last Verified

2026-06-12 — verified accurate against `mcp_server.py`, `src/doge/interfaces/mcp/server.py`, and `docs/MCP_SERVER.md` on branch `cdd-adoption-2026-06-11` post Phase-2 soft-delete fix.

## Decision Makers

WSMAN, Codex

## Summary

MY-DOGE-MICRO's MCP server (`doge-db`) exposes 6 read-only analytical tools and must serve two distinct consumers — the local Claude Code client (process-coupled) and web/remote HTTP clients (network-coupled). This ADR records the decision to support **stdio as the primary transport** and **SSE as the secondary transport** from a single `FastMCP` server, with DuckDB zero-copy reads over the SQLite price databases and a 30-second per-tool latency budget enforced uniformly via an `asyncio.wait_for` wrapper.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python 3.10+, MCP SDK 1.25.0 (`mcp.server.fastmcp.FastMCP`), Starlette (SSE app), Uvicorn 0.38.0, DuckDB 1.4.4 (sqlite extension), SQLite 3 |
| **Domain** | Interface / integration transport, analytical read path, local-first deployment |
| **Knowledge Risk** | MEDIUM — MCP SDK 1.25.0 is near training cutoff; the `FastMCP.custom_route` and `sse_app()` APIs were verified against the installed `mcp` package and `tests/test_transport.py` (stdio `initialize` handshake + SSE `/health`, `/metrics`, `/sse` all green). |
| **References Consulted** | `docs/MCP_SERVER.md`, `docs/reference/python/VERSION.md`, `standards/technical-preferences.md` (MCP Tool Latency budget), `.mcp.json`, `scripts/mcp_stdio.bat`, `scripts/start_mcp_sse.sh` |
| **Post-Cutoff APIs Used** | `FastMCP.custom_route`, `FastMCP.sse_app`, `mcp.server.stdio.stdio_server(stdout=...)` — all present in the installed `mcp==1.25` package; the Windows `stdout` double-`TextIOWrapper` workaround (`mcp_server.py:479-500`) is required by the installed SDK's internal `TextIOWrapper(sys.stdout.buffer, encoding="utf-8")` construction. |
| **Verification Required** | `python -m pytest tests/test_mcp_tools.py tests/test_transport.py -q` stays green (77 tests); SSE startup on a free port via `tests/test_transport.py::TestSseTransport`. |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0001 (brownfield-clean-architecture — interface/adapter boundary the MCP server sits inside), ADR-0002 (centralized-configuration — `MCPConfig` defines `tool_timeout`, `sse_host`, `sse_port`), ADR-0003 (storage-repository-contract — DuckDB zero-copy read model the tools depend on) |
| **Enables** | CDD module #8 `mcp-server`; future ADRs for the FastAPI service (#9) transport boundary and the Vue Web Console (#11) which consumes SSE-side `/health` + `/metrics` for liveness. |
| **Blocks** | No story may add a third MCP transport (e.g. WebSocket, streamable-HTTP) without superseding this ADR. No story may relax the 30s `tool_timeout` without amending the performance budget in `standards/technical-preferences.md`. |
| **Ordering Note** | The monolithic `mcp_server.py` (legacy, direct-DB) and the modular `src/doge/interfaces/mcp/server.py` (service-delegating) coexist per ADR-0001's brownfield-migration rule; this ADR governs the transport strategy for **both** until the modular server is the sole entrypoint. |

## Context

### Problem Statement

The MCP server is the AI-facing analytical surface of a local-first quant tool. It must be reachable by (a) Claude Code, which spawns the server as a child process and speaks JSON-RPC over the process's stdin/stdout, and (b) the local Vue Web Console and any remote MCP-aware client, which reach it over HTTP. A single transport cannot serve both well: stdio cannot be reached by a browser; an HTTP server cannot be spawned transparently by a code editor. The decision must also pin the read model (DuckDB zero-copy over SQLite) and the latency budget so that all six tools behave identically regardless of transport.

### Current State

- `mcp_server.py` is the live, registered entrypoint (`.mcp.json` points `doge-db` at `scripts/mcp_stdio.bat` → `python mcp_server.py`). It defines all six tools inline (`mcp_server.py:266-431`), opens DuckDB connections directly via `ai_analysis.get_duckdb_connection` (legacy path), and opens the research SQLite directly for `stock_overview` notes (`mcp_server.py:340-360`).
- `src/doge/interfaces/mcp/server.py` is the modular mirror that delegates the same six tools to `doge.core.services` via `doge.interfaces.mcp.tools.*`. It is a drop-in replacement per its docstring but is **not yet the registered entrypoint** (ADR-0001 brownfield coexistence).
- Both servers use an identical `_timed` decorator wrapping `asyncio.wait_for(fn, timeout=TOOL_TIMEOUT)` with `TOOL_TIMEOUT = 30`.
- The Windows stdio path requires a workaround (`mcp_server.py:479-500`): the MCP SDK internally wraps `sys.stdout.buffer` in a second `TextIOWrapper`, and on Windows two wrappers flushing one `BufferedWriter` raise `OSError`. The fix saves `sys.stdout.buffer`, replaces `sys.stdout` with a `StringIO`, and passes a custom wrapped stdout to `stdio_server(stdout=...)`.
- `MCPConfig` (`src/doge/config/settings.py:67-73`) owns `tool_timeout=30`, `stdio_transport="stdio"`, `sse_host="127.0.0.1"`, `sse_port=8902`.

### Constraints

- **Local-first**: the server must start with no network dependency and bind to loopback by default.
- **Read-only analytical path**: DuckDB attaches the SQLite price DBs read-only (`duckdb.py:42` `read_only=True`); only `refresh_views` opens write mode. MCP tools must never write.
- **30s latency budget**: `standards/technical-preferences.md` pins "MCP Tool Latency: within 30 seconds"; the `vw_market_breadth_cn` 730-day view and the `vw_rsrs_ranking_*` 200-row regressions must complete within it.
- **Determinism for AI clients**: every tool must return a string; errors must be returned as `"Error: ..."` strings (not raised) so the MCP client always receives a textual result.
- **Cross-platform**: Windows is a first-class target (project runs on Windows 10 LTSC); the stdio workaround is mandatory there.

### Requirements

- Support stdio (primary, for Claude Code) and SSE (secondary, for web/remote) from one server.
- Enforce a uniform per-tool timeout that matches the documented budget.
- Zero-copy DuckDB reads over the SQLite price databases for all analytical tools.
- Health and metrics endpoints available on the SSE transport for liveness/observability.
- Input validation (market whitelist, ticker charset, int/float bounds) applied identically on both transports.

## Decision

Adopt a **dual-transport single-server** strategy:

1. **Primary transport: stdio.** `python mcp_server.py --transport stdio` is the default and the registered Claude Code entrypoint (`.mcp.json`). It speaks JSON-RPC over the process stdin/stdout and is process-coupled to the editor. The Windows `stdout` double-wrapper workaround is applied (`mcp_server.py:479-500`).
2. **Secondary transport: SSE.** `python mcp_server.py --transport sse --host 127.0.0.1 --port 8902` runs `uvicorn.run(mcp.sse_app(), ...)` and exposes the same six tools plus two HTTP routes: `GET /health` and `GET /metrics`. Bound to loopback by default; binding to `0.0.0.0` is an operator decision with security implications (see Configuration Knobs / Risks).
3. **Uniform latency budget.** `TOOL_TIMEOUT = 30` (matching `MCPConfig.tool_timeout` and `standards/technical-preferences.md`). The `_timed` decorator wraps every tool in `asyncio.wait_for(..., timeout=TOOL_TIMEOUT)`; on timeout it returns `"Error: {tool} timed out after 30s"` and on exception returns `"Error: {type}: {msg}"`. No tool raises to the MCP client.
4. **Zero-copy DuckDB reads.** All analytical tools (`query_stock`, `rsrs_ranking`, `market_breadth`, `volume_anomalies`, `list_views`) and the price block of `stock_overview` read through `get_duckdb_connection()`, which attaches the CN/US SQLite files via the DuckDB `sqlite` extension in read-only mode. No OHLCV is duplicated into DuckDB; only view definitions live in `market.duckdb`.
5. **Validation at the tool boundary.** `_validate_market` (whitelist `{"cn","us"}`), `_validate_ticker` (charset `^[A-Za-z0-9.\-]+$`, length, suffix-normalization), `_validate_int`, `_validate_float` run before any DB access on both transports.

### Architecture

```text
  Claude Code                 Vue Web Console / remote MCP client
       |                                  |
       | spawn + JSON-RPC                 | HTTP (SSE)
       v                                  v
  +-----------------------------------------------+
  |        FastMCP("doge-db")  (one server)       |
  |  --transport stdio (default)                  |
  |  --transport sse   (--host --port)            |
  |                                               |
  |  6 tools  (identical on both transports)      |
  |    query_stock | stock_overview | rsrs_ranking|
  |    market_breadth | volume_anomalies|list_views|
  |  + GET /health, GET /metrics  (SSE only)      |
  |                                               |
  |  _timed decorator: asyncio.wait_for(timeout=30)|
  +-----------------------------------------------+
          |                  |              |
          | DuckDB           | DuckDB       | sqlite3 (notes, names)
          | read-only        | read-only    | (stock_overview only)
          v                  v              v
     market.duckdb  ---ATTACH(read_only)--->  market_data_cn.db
                         (zero-copy)          market_data_us.db
                                              research_insights.db
```

### Key Interfaces

```python
# Transport selection (mcp_server.py:462-504)
python mcp_server.py --transport {stdio,sse} [--host 127.0.0.1] [--port 8902] [--log-level INFO]

# Tool contract — every tool: async, returns str, never raises to client
@mcp.tool()
@_timed("query_stock")
async def query_stock(ticker: str, market: str = "cn", days: int = 20) -> str: ...

# Timeout / error contract (mcp_server.py:160-194)
TOOL_TIMEOUT = 30
# success  -> returns the formatted string
# timeout  -> "Error: {tool_name} timed out after {TOOL_TIMEOUT}s"
# exception-> "Error: {ExcType}: {msg}"

# SSE-only health/metrics
@mcp.custom_route("/health", methods=["GET"])   # {"status": "ok"} | 503 {"status":"error","detail":...}
@mcp.custom_route("/metrics", methods=["GET"])  # Prometheus-text inside {"metrics": "..."}
```

### Implementation Guidelines

- Both transports MUST expose the identical six tools with identical signatures and validation. The modular server (`src/doge/interfaces/mcp/server.py`) is the future single source; until ADR-0001 migration completes, the two must be kept in sync.
- The `_timed` decorator MUST wrap the tool body, not the validation, so that validation errors are still caught and returned as `"Error: ..."` strings (test `test_query_stock_invalid_market` pins this).
- New tools must declare Chinese descriptions (per `test_tools_descriptions_are_chinese`) and be added to both `mcp_server.py` and `src/doge/interfaces/mcp/tools/`.
- The `stock_overview` notes read MUST filter `deleted_at IS NULL` when the column exists (Phase-2 consistency fix; see CDD #7 §3.3 and #8 bug fix) — the raw sqlite read must not leak soft-deleted notes.

## Alternatives Considered

### Alternative 1: stdio only

- **Description**: Ship only the stdio transport; web clients use the FastAPI service (#9) instead of MCP.
- **Pros**: Smallest surface; no second port; no HTTP exposure.
- **Cons**: Removes the ability for a remote/MCP-native client (or the web console's liveness probe against `/health`) to reach the analytical tools directly; forces a parallel FastAPI re-implementation of the six tools.
- **Estimated Effort**: Lower for the server, higher overall (duplicate tooling).
- **Rejection Reason**: The MCP server is intended to be the canonical AI/remote analytical surface; dropping SSE would fragment the interface.

### Alternative 2: SSE only

- **Description**: Run only the HTTP server; have Claude Code connect over loopback HTTP.
- **Pros**: Single transport code path.
- **Cons**: Claude Code's native MCP integration spawns a stdio child process via `.mcp.json`; an HTTP-only server cannot be registered that way. Operators would have to keep a long-running server up before launching the editor.
- **Estimated Effort**: Medium.
- **Rejection Reason**: Breaks the zero-config "editor spawns the server" UX that `.mcp.json` + stdio provides.

### Alternative 3: Streamable-HTTP (newer MCP transport)

- **Description**: Adopt the post-2024 streamable-HTTP transport instead of SSE.
- **Pros**: Single request-response channel, simpler than SSE for some clients.
- **Cons**: The pinned `mcp==1.25.0` SDK's `sse_app()` is the stable, tested surface; streamable-HTTP support is newer and not exercised by `tests/test_transport.py`. Adopting it now would require an SDK upgrade and new transport tests.
- **Estimated Effort**: Higher (SDK upgrade + new tests).
- **Rejection Reason**: Premature; SSE is verified green and sufficient for the local-first web client. Revisit when the SDK is upgraded.

## Consequences

### Positive

- One server, two transports, identical tool behaviour — no AI-client-visible difference between local and remote use.
- stdio gives Claude Code zero-config spawn-on-demand; SSE gives the web console a stable HTTP surface with liveness/metrics.
- The 30s timeout and `"Error: ..."` string contract make every tool deterministic from the client's perspective — no unhandled exceptions cross the transport.
- Zero-copy DuckDB reads keep memory bounded (no full-market duplication) and reads concurrent-safe (read-only attach).

### Negative

- Two coexisting server implementations (`mcp_server.py` and `src/doge/interfaces/mcp/server.py`) must be kept in sync until ADR-0001 migration completes — a drift risk.
- The Windows stdio workaround is fragile: it depends on the SDK's internal `TextIOWrapper` construction; an SDK upgrade that changes how it wraps stdout could resurrect `OSError`.
- SSE bound to `0.0.0.0` would expose the (unauthenticated) MCP tools to the LAN. Default is loopback, but the footgun exists.
- The 30s timeout is a hard ceiling: a pathological DuckDB view scan (e.g. a 730-day breadth recompute under load) could be truncated, returning a confusing timeout error string.

### Neutral

- The `doge_mcp.py` shim (another stdio entrypoint) exists alongside `mcp_server.py`; this ADR treats `mcp_server.py` as canonical and `doge_mcp.py` as a compatibility alias.

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Monolithic and modular servers drift (tool signature / validation divergence) | Medium | High | `tests/test_mcp_tools.py` asserts the exact tool set + Chinese descriptions on the live server; a parallel test against the modular `create_mcp_server()` is an open acceptance criterion (CDD #8 §8). |
| Windows stdio workaround breaks on SDK upgrade | Medium | High | The workaround is unit-tested only implicitly via `tests/test_transport.py::TestStdioTransport::test_stdio_initialize`; pin `mcp==1.25.0` until re-verified. |
| SSE exposed beyond loopback | Low | High | Default `sse_host=127.0.0.1`; documented in Configuration Knobs that `0.0.0.0` is an explicit operator choice. |
| Tool exceeds 30s under load | Low | Medium | `_timed` returns a clear timeout string; `vw_market_breadth_cn` (730d) is the worst-case view — monitor via `/metrics` `mcp_request_duration_seconds`. |
| `stock_overview` notes leak soft-deleted rows (Phase-2 gap) | Was High → Fixed | High | Fixed in this pass: `mcp_server.py:340-360` now detects `deleted_at` and filters `IS NULL`; pinned by `tests/test_mcp_notes_softdelete.py`. |

## Performance Implications

| Metric | Before | Expected After | Budget |
|--------|--------|----------------|--------|
| MCP common query latency (single tool) | ~0.4s observed (`query_stock` per logs) | Unchanged — fix only touches the notes sub-query | < 30s (`tool_timeout`) |
| `stock_overview` notes sub-query | 1 `COUNT` + 1 `SELECT` (no `deleted_at` predicate) | Same 2 queries + `PRAGMA table_info` once + `deleted_at IS NULL` predicate | Negligible overhead (PRAGMA is cached by SQLite per connection; predicate uses an existing nullable column, no index needed at local-first scale) |
| SSE startup | ~1-2s (uvicorn + DuckDB pre-warm) | Unchanged | No regression |
| stdio handshake | < 1s | Unchanged | No regression |

## Migration Plan

This ADR documents an already-implemented strategy; no migration is required. The forward migration (owned by ADR-0001 / CDD #12) is to retire the monolithic `mcp_server.py` in favour of `src/doge/interfaces/mcp/server.py` once its tool outputs are verified byte-identical to the legacy server's.

1. **Done**: dual transport live; 30s timeout; zero-copy reads; Phase-2 soft-delete consistency fix applied.
2. **Next (CDD #12)**: add a parity test asserting `src/doge/interfaces/mcp/server.create_mcp_server()` produces the same tool set and validation behaviour as `mcp_server.py`.
3. **Future**: switch `.mcp.json` to launch the modular server; delete the monolith.

**Rollback plan**: revert `.mcp.json` to point at `scripts/mcp_stdio.bat` → `mcp_server.py` (the current canonical entrypoint). The monolith remains the rollback target until the modular server passes parity tests.

## Validation Criteria

- [x] `python -m pytest tests/test_mcp_tools.py tests/test_transport.py -q` passes (77 tests, verified 2026-06-12).
- [x] stdio `initialize` handshake returns `serverInfo.name == "doge-db"` (`tests/test_transport.py::TestStdioTransport`).
- [x] SSE `/health`, `/metrics`, `/sse` all return 200 (`tests/test_transport.py::TestSseTransport`).
- [x] All six tools are registered and have non-empty Chinese descriptions (`tests/test_mcp_tools.py::TestToolsNotPresent`).
- [x] `_timed` enforces the 30s timeout and returns `"Error: ..."` on timeout/exception (`tests/test_mcp_tools.py::TestTimedDecorator`).
- [x] `stock_overview` excludes soft-deleted notes (`tests/test_mcp_notes_softdelete.py`, added in this pass).
- [ ] Parity test: modular `create_mcp_server()` exposes the same six tools with matching signatures (OPEN — CDD #12).
- [ ] `.mcp.json` points at the modular server once parity is proven (OPEN — CDD #12).

## CDD Requirements Addressed

| CDD Document | System | Requirement | How This ADR Satisfies It |
|--------------|--------|-------------|---------------------------|
| `design/cdd/mcp-server.md` (#8) | MCP Server | "stdio is primary (Claude Code), SSE is secondary (web/remote)" | Decision §1–§2 record the dual-transport roles and the loopback default. |
| `design/cdd/mcp-server.md` (#8) | MCP Server | "DuckDB reads are zero-copy over SQLite (read-only attach)" | Decision §4 + Architecture diagram pin the read-only ATTACH model; cross-refs ADR-0003. |
| `design/cdd/mcp-server.md` (#8) | MCP Server | "single-tool latency budget <30s" | Decision §3 + `TOOL_TIMEOUT=30` enforced by `_timed`/`asyncio.wait_for`. |
| `design/cdd/mcp-server.md` (#8) | MCP Server | "soft-deleted notes must not leak into MCP responses" (Phase-2 consistency) | Risks table + the applied fix at `mcp_server.py:340-360`, pinned by `tests/test_mcp_notes_softdelete.py`. |
| `design/cdd/runtime-configuration.md` (#1) | Runtime Configuration | `MCPConfig` owns `tool_timeout`, `sse_host`, `sse_port` | This ADR consumes those settings as the transport contract. |

## Related

- [ADR-0001](adr-0001-brownfield-clean-architecture.md) — interface/adapter boundary the MCP server sits inside; governs the monolithic-vs-modular coexistence.
- [ADR-0002](adr-0002-centralized-configuration.md) — `MCPConfig` source of the timeout/host/port settings.
- [ADR-0003](adr-0003-storage-repository-contract.md) — DuckDB zero-copy read model the analytical tools depend on.
- `design/cdd/mcp-server.md` (module #8) — the full reverse-documented CDD.
- `design/cdd/research-insight-knowledge-base.md` (module #7) — owns the `stock_notes` soft-delete contract this ADR's fix enforces.
- Code: `mcp_server.py`, `src/doge/interfaces/mcp/server.py`, `.mcp.json`, `scripts/mcp_stdio.bat`, `scripts/start_mcp_sse.sh`.
- Tests: `tests/test_mcp_tools.py`, `tests/test_transport.py`, `tests/test_mcp_notes_softdelete.py`.
