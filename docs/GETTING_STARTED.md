# MY-DOGE-MICRO — Getting Started (Product Operator Guide)

> **Not the doc you think this is?** `docs/QUICK-START.md` is the *CDD-framework*
> onboarding guide for the Claude Code agent studio (53 agents, skills,
> governance). **This file** is the getting-started guide for the **MY-DOGE-MICRO
> product** — the local-first quantitative investment decision-support platform.
> The two share a name pattern but address completely different audiences.

## Overview

MY-DOGE-MICRO is a local-first quantitative investment decision-support platform.
All data, computation, and state live on the operator's machine; no cloud
account is required. The product exposes **three runtime surfaces**, each bound
to loopback so it is safe to run on a developer workstation:

| Surface | Entry point | Default bind | Purpose |
|---------|-------------|--------------|---------|
| **PyQt desktop dashboard** | `src/interface/dashboard.py` | local GUI window | Operator scan / macro / notes UI |
| **FastAPI HTTP backend** | `src/api/main.py` | `127.0.0.1:8901` | REST + SSE API consumed by the web console |
| **MCP server** | `doge_mcp.py` | stdio, or `127.0.0.1:8902` (SSE) | Tool layer for Claude Code / MCP clients |

You do not need all three at once. The two most common setups are:

- **MCP-only** (Claude Code integration) — start the stdio MCP server.
- **Web console** — start the FastAPI backend and the Vite dev server.

## Prerequisites

- **Python 3.10+** (`pyproject.toml` declares `requires-python = ">=3.10"`).
- **Windows 10 LTSC** is the primary target platform. POSIX shell equivalents
  are shipped (`scripts/*.sh`) for macOS / Linux.
- A local Python environment (project venv recommended; the start scripts
  auto-detect `venv/Scripts/python.exe` on Windows or `venv/bin/python` on POSIX).
- **Optional extras** (install only what you need):
  - `[gui]` → `PyQt6` (desktop dashboard)
  - `[tdx]` → `opentdx` (TDX market-data downloader)
  - `[cn]` → `akshare` (A-share supplementary data)
- A DeepSeek API key, **only** if you intend to run the LLM macro strategy
  engine (Module #4) or the desktop dashboard's Analysis tab. See
  [Configure environment variables](#configure-environment-variables).

## Install

From the project root, choose one of the two equivalent install paths:

**Editable install from `pyproject.toml` (recommended — pulls extras by name):**

```bash
pip install -e .            # core runtime
pip install -e ".[gui]"     # + desktop dashboard (PyQt6)
pip install -e ".[tdx,cn]"  # + TDX downloader + akshare
```

**Pinned install from `requirements.txt` (reproduces the exact tested versions):**

```bash
pip install -r requirements.txt
```

`requirements.txt` pins the core stack (`duckdb==1.4.4`, `mcp==1.25.0`,
`fastapi==0.123.8`, `uvicorn==0.38.0`, `sse-starlette==3.0.3`,
`pydantic==2.12.4`, `openai==1.62.0`, `yfinance==0.2.66`, …). It does not
declare optional extras — install PyQt6 / opentdx / akshare separately if you
use the equivalent `requirements.txt` path and need those surfaces.

## Configure environment variables

All runtime configuration is centralized in
`src/doge/config/settings.py` (ADR-0002, single source of truth). Environment
variables are the override mechanism; every value below has a safe default and
is read via the `_env_path` / `_env_int` helpers (`settings.py:18-49`).

> The table below is a **superset** of the `DBConfig` + `MCPConfig` + `MarketConfig`
> dataclass fields. The docs-consistency test
> (`tests/cli/test_getting_started_links.py`) enforces this invariant so the doc
> cannot drift from `settings.py`.

### Database paths (`DBConfig`, `settings.py:52-67`)

| Variable | Default | Description |
|----------|---------|-------------|
| `DOGE_DB_DIR` | `<project_root>/data` | Root directory for all local databases. |
| `DOGE_CN_DB` | `{DOGE_DB_DIR}/market_data_cn.db` | A-share OHLCV SQLite database. |
| `DOGE_US_DB` | `{DOGE_DB_DIR}/market_data_us.db` | US-equity OHLCV SQLite database. |
| `DOGE_RESEARCH_DB` | `{DOGE_DB_DIR}/research_insights.db` | Research notes + stock names SQLite database. |
| `DOGE_DUCKDB_PATH` | `{DOGE_DB_DIR}/market.duckdb` | DuckDB analytical file (attached read-only to the SQLite sources for cross-database views). |
| `DOGE_VIEWS_SQL_TRACKED` | `src/doge/infrastructure/database/views.sql` | Canonical, version-controlled DuckDB view DDL (S003-005). Preferred by the refresh path over the `data/views.sql` mirror when present. |

> `DOGE_DUCKDB_PATH` is documented here but is currently **omitted** from the
> older `docs/MCP_SERVER.md` env-var table (`docs/MCP_SERVER.md:386-389`) — a
> pre-existing doc gap this guide reconciles.

### Market behavior (`MarketConfig`, `settings.py:112`)

| Variable | Default | Description |
|----------|---------|-------------|
| `DOGE_RETENTION_DAYS` | `730` | Per-ticker destructive prune ceiling applied on every OHLCV write. **Must be `>= 730`** to satisfy the widest analytical-view window (`vw_market_breadth_cn` uses `INTERVAL 730 DAYS`). This knob is **DESTRUCTIVE** — every write deletes rows older than N days per ticker. |

### MCP server (`MCPConfig`, `settings.py:128-134`)

The SSE start scripts honor `MCP_HOST` / `MCP_PORT` shell variables (see
`scripts/start_mcp_sse.bat:17-18`, `scripts/start_mcp_sse.sh:19-20`); the
matching dataclass defaults are the source of truth:

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_HOST` | `127.0.0.1` | SSE bind address (loopback by default). |
| `MCP_PORT` | `8902` | SSE listen port. |
| `MCP_TOOL_TIMEOUT` (dataclass: `tool_timeout`) | `30` | Per-tool execution ceiling in seconds. |

### DeepSeek API key (S002-013 — required for macro / LLM surfaces)

`DEEPSEEK_API_KEY` is the **PRIMARY** key source for the macro strategy engine
(Module #4) and the desktop Analysis tab. Resolution order in
`src/macro/config.py:163-200`:

1. `DEEPSEEK_API_KEY` env var — if set and non-empty, it wins.
2. Otherwise, if `models_config.json` still carries the placeholder sentinel
   `REPLACE_WITH_DEEPSEEK_API_KEY` (which it ships with), the constructor
   raises `RuntimeError` with an actionable remediation message. The
   placeholder MUST NOT flow to the OpenAI client.

`models_config.json` ships only the placeholder; **the real key is never
committed.** Set the env var before launching any macro run or the GUI:

**Windows (cmd.exe):**

```cmd
set DEEPSEEK_API_KEY=sk-your-real-key-here
```

**Windows (PowerShell):**

```powershell
$env:DEEPSEEK_API_KEY='sk-your-real-key-here'
```

**macOS / Linux (bash):**

```bash
export DEEPSEEK_API_KEY=sk-your-real-key-here
```

To switch LLM models at runtime (used by the GUI model-switcher), also export
`DEEPSEEK_MODEL` (e.g. `deepseek-chat` or `deepseek-reasoner`).

> **Security verification for operators:** a forensic audit of the repository
> confirmed that no real DeepSeek key was ever committed to git history
> (`models_config.json` was gitignored from the initial commit; no `sk-...`
> key appears in 82 commits, 4 refs, reflog, or dangling objects). The code
> remediation (placeholder swap + env-var read) shipped with S002-013. The
> **operator must export `DEEPSEEK_API_KEY`** and verify that
> `python -m macro.cli` works. No key rotation or history rewrite is required.
> See `docs/MCP_SERVER.md` "Operator action — key verification".

## Start the MCP server

The MCP server has two transports. Both start scripts auto-detect a project
venv (`venv/Scripts/python.exe` on Windows, `venv/bin/python` or
`.venv/bin/python` on POSIX) and fall back to `python` / `python3` in `PATH`.

**stdio (for Claude Code integration):**

```bash
# Windows
scripts\mcp_stdio.bat
# macOS / Linux
./scripts/mcp_stdio.sh
```

Both invoke `doge_mcp.py --transport stdio`
(`scripts/mcp_stdio.bat:18`, `scripts/mcp_stdio.sh:18`). The project-level
`.mcp.json` registers `doge-db` against `scripts\mcp_stdio.bat` for Claude Code.

`doge_mcp.py` is the canonical repo-root MCP entrypoint; the old monolithic
entrypoint has been retired.

**SSE (for the web console or any HTTP MCP client):**

```bash
# Windows
scripts\start_mcp_sse.bat
# macOS / Linux — override host/port via env if needed
MCP_HOST=127.0.0.1 MCP_PORT=8902 ./scripts/start_mcp_sse.sh
```

Both invoke `doge_mcp.py --transport sse --host … --port …`
(`scripts/start_mcp_sse.bat:21`, `scripts/start_mcp_sse.sh:23`) and default
`MCP_HOST=127.0.0.1`, `MCP_PORT=8902` if unset.

## Start the FastAPI backend

```bash
python src/api/main.py
```

Binds `127.0.0.1:8901` (`src/api/main.py:118-120`). This process serves the
REST + SSE API consumed by the Vue web console. It registers six routers under
`/api/{scan,data,notes,macro,analysis,config}` plus `/api/health` and
`/api/stats` (`src/api/main.py:83-115`).

The API uses a stable error envelope — every `HTTPException` is reshaped into
`{"error": {"code", "message"}}` with string-enum codes
(`bad_request` / `not_found` / `conflict` / `unprocessable` / `internal_error`,
`src/api/main.py:33-57`); unhandled exceptions return a fixed operator-safe
`internal server error` body with no stack-trace leak (`src/api/main.py:60-74`).

> **Local-only safety boundary.** The server binds `127.0.0.1` and CORS is
> `allow_origins=["*"]` (`src/api/main.py:26-31`) — acceptable *only* because
> the bind address prevents remote access. Binding to `0.0.0.0` would expose
> the API with no authentication; do not do this on a shared host.
> CORS hardening is tracked under ADR-0007 (Proposed).

## Start the web console

```bash
cd web
npm install
npm run dev
```

The Vite dev server proxies `/api` → `http://localhost:8901`
(`web/vite.config.ts:15-19`), so the FastAPI backend must be running first.

> **No sibling-project checkout required.** The `@pretext` layout library is
> **vendored** into `web/src/vendor/pretext/` (S002-012 / TR-037, see the
> comment header in `web/vite.config.ts:5-7`). The alias `@pretext` resolves
> to `web/src/vendor/pretext/layout.ts`, so the web app builds on a clean
> checkout. To re-sync the vendored copy, follow
> `web/src/vendor/pretext/README.md`.

## Start the desktop dashboard

```bash
pip install -e ".[gui]"     # installs PyQt6
python src/interface/dashboard.py
```

> **Known portability blocker.** `src/interface/dashboard.py:6-15` contains a
> **machine-hardcoded** Qt6 DLL bootstrap:
>
> ```python
> qt6_bin_path = r"E:\LLMs\miniconda3\Lib\site-packages\PyQt6\Qt6\bin"
> ```
>
> On any machine whose PyQt6 is not installed at that exact path, the dashboard
> prints `⚠️ Qt6 DLL path not found: …` and may fail to load Qt libraries. To
> run it elsewhere, either edit the path to your local PyQt6 `Qt6\bin` location
> or remove the block if your environment resolves Qt DLLs via `PATH`
> normally. This is tracked as a clean-architecture migration cleanup item, not
> a configuration knob.

## First scan walkthrough

The fastest end-to-end path with **no LLM key required** (pure analytics):

1. Ensure the SQLite databases exist under `data/` (or wherever `DOGE_DB_DIR`
   points). If they are missing, populate them via the TDX downloader
   (`pip install -e ".[tdx]"` then `python src/micro/tdx_downloader.py`) or
   `yfinance`.
2. Start the FastAPI backend (`python src/api/main.py`).
3. Open the web console (`cd web && npm run dev`) and use the **Scanner** tab,
   **or** drive the query CLI directly:
   ```bash
   python src/cli.py rsrs --market cn --top 10       # RSRS momentum ranking
   python src/cli.py breadth --market cn --days 7    # market breadth
   python src/cli.py anomaly --min-ratio 5.0          # volume anomalies
   ```
   Full command reference: see the CLI doc (Next steps below).

To run the **LLM macro strategy report** (requires `DEEPSEEK_API_KEY`):

```bash
python -m macro.cli
```

## Verification smoke

Confirm each surface is up with a one-line health check:

```bash
# MCP SSE server (must be started in SSE mode first)
curl http://127.0.0.1:8902/health
# → {"status": "ok"}   (doge_mcp.py routes through src/doge/interfaces/mcp/server.py)

# FastAPI backend
curl http://127.0.0.1:8901/api/health
# → {"status":"ok"}     (src/api/main.py:91-93)
```

If the MCP `/health` call fails, the DuckDB attach to the SQLite sources could
not be established — check `DOGE_DB_DIR` and that the `*.db` files exist.

## Next steps

- **HTTP API reference** — `docs/API.md` (Wave 2; enumerates all routes,
  schemas, the SSE contract, and the error-envelope codes).
- **CLI command reference** — `docs/CLI.md` (Wave 2; the `doge` query CLI and
  the `macro.cli` macro CLI).
- **Operations runbook** — `docs/operations-runbook.md` (Wave 2; key environment
  verification, database backup, retention tuning, log inspection).
- **MCP tool catalog** — `docs/MCP_SERVER.md` (the six read-only analytical
  tools and the DuckDB views behind them).
- **Configuration source of truth** — `src/doge/config/settings.py` and
  ADR-0002 (centralized configuration).
