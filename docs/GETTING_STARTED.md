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
| **FastAPI HTTP backend** | `src/doge/interfaces/api/main.py` | `127.0.0.1:8901` | REST + SSE API consumed by the web console |
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
| `DOGE_AGENT_DB` | `{DOGE_DB_DIR}/agent_state.db` | Research Copilot sessions, runs, events, artifacts, approvals, documents, and daemon queue metadata. |
| `DOGE_DOCUMENT_STORAGE_DIR` | `{DOGE_DB_DIR}/documents` | Stored payloads for real Research Copilot file uploads and CLI `/attach`. |
| `DOGE_DOCUMENT_MAX_BYTES` | `104857600` | Maximum accepted document upload size, 100 MB by default. |
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
> (no `sk-...` key appears in 82 commits, 4 refs, reflog, or dangling
> objects). The code
> remediation (placeholder swap + env-var read) shipped with S002-013. The
> **operator must export `DEEPSEEK_API_KEY`** and verify that
> `python -m macro.cli` works. No key rotation or history rewrite is required.
> See `docs/MCP_SERVER.md` "Operator action — key verification".

### Kimi / Moonshot variables (Research Copilot demo)

The Research Copilot demo uses `src/doge/config/settings.py::KimiConfig` and
the OpenAI-compatible Moonshot endpoint. If `MOONSHOT_API_KEY` is absent, the
demo runtime falls back to a deterministic scripted model so local tests and
the web workspace still run.

Real file upload and CLI `/attach` do not require a Kimi key. When
`MOONSHOT_API_KEY` is present, the file upload service can also call the Kimi
Files API adapter; when it is absent, the local deterministic parser stores
hash/MIME/size metadata and offline parsed content.

| Variable | Default | Description |
|----------|---------|-------------|
| `MOONSHOT_API_KEY` | unset | Secret for live Kimi calls. Keep it in the shell environment only. |
| `KIMI_BASE_URL` | `https://api.moonshot.ai/v1` | OpenAI-compatible API base URL. |
| `KIMI_GENERAL_MODEL` | `kimi-k2.6` | General research/planning/finalization model. |
| `KIMI_CODE_MODEL` | `kimi-k2.7-code` | Code-sub-agent model for Python/SQL/data tasks. |
| `KIMI_MAX_RETRIES` | `2` | Bounded retries for Kimi chat create calls on rate-limit/transient provider errors. |
| `KIMI_RETRY_DELAY` | `1.0` | Delay in seconds between Kimi chat retries; set to `0` only for local tests. |
| `KIMI_MAX_COMPLETION_TOKENS` | `16384` | Maximum generated tokens for Kimi calls; preferred over deprecated provider `max_tokens`. |
| `KIMI_TIMEOUT_SECONDS` | `60.0` | Client timeout for Kimi chat requests. |
| `KIMI_BACKOFF_BASE_SECONDS` | `1.0` | Initial exponential-backoff delay for retryable Kimi failures. |
| `KIMI_BACKOFF_MAX_SECONDS` | `60.0` | Maximum retry backoff for Kimi calls. |
| `KIMI_COST_TRACKING_ENABLED` | `true` | Enables usage/cost fields in model response metadata when provider usage is available. |
| `KIMI_PROMPT_CACHE_ENABLED` | `false` | Enables `prompt_cache_key` for enterprise/session calls. |
| `KIMI_MONTHLY_BUDGET_USD` | `0.0` | Operator budget metadata knob; `0.0` means no enforced monthly budget in the local demo. |
| `KIMI_RUN_BUDGET_USD` | `0.0` | Per-run budget metadata knob; `0.0` means no enforced run budget by default. |

The no-key fallback is intentional: without `MOONSHOT_API_KEY`, Research
Copilot still runs with a scripted local model, `/v1/documents` still persists
real file metadata, and CLI `/attach` still produces a real `document_id`.

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
python -m uvicorn doge.interfaces.api.main:app --host 127.0.0.1 --port 8901
```

Binds `127.0.0.1:8901` (`src/doge/interfaces/api/main.py`). This process serves the
REST + SSE API consumed by the Vue web console. It registers six routers under
`/api/{scan,data,notes,macro,analysis,config}` plus `/api/health` and
`/api/stats` (`src/doge/interfaces/api/main.py`).

The API uses a stable error envelope — every `HTTPException` is reshaped into
`{"error": {"code", "message"}}` with string-enum codes
(`bad_request` / `not_found` / `conflict` / `unprocessable` / `internal_error`,
`src/doge/interfaces/api/main.py`); unhandled exceptions return a fixed operator-safe
`internal server error` body with no stack-trace leak (`src/doge/interfaces/api/main.py`).

> **Local-only safety boundary.** The server binds `127.0.0.1` and CORS is
> `allow_origins=["*"]` (`src/doge/interfaces/api/main.py`) — acceptable *only* because
> the bind address prevents remote access. Binding to `0.0.0.0` would expose
> the API with no authentication; do not do this on a shared host.
> ADR-0007 is Accepted with this loopback-guaranteed posture. CORS hardening
> and auth are still required before any non-loopback bind.

`src/api` remains only as a deprecated compatibility redirect shim. New
integrations and operator commands should use `doge.interfaces.api`.

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

   > **First-run yfinance rate-limiting.** Yahoo throttles unauthenticated
   > `yfinance` calls (HTTP 429 Too Many Requests). On a cold start the
   > `YFinanceDataSource` adapter degrades safely to `None` after a bounded
   > retry — no crash, no DB corruption. Wait a few minutes and retry, or use
   > the TDX downloader for CN bulk ingest (it is not rate-limited). This is
   > environmental, not a code defect.
2. Run the 5-minute demo to see the bundled analytical data without any
   configuration:
   ```bash
   doge demo
   ```
3. Start the FastAPI backend (`python -m uvicorn doge.interfaces.api.main:app --host 127.0.0.1 --port 8901`).
4. Open the web console (`cd web && npm run dev`) and use the **Scanner** tab,
   **or** drive the query CLI directly:
   ```bash
   doge rsrs --market cn --top 10       # RSRS momentum ranking
   doge breadth --market cn --days 7    # market breadth
   doge anomaly --min-ratio 5.0          # volume anomalies
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
# → {"status":"ok"}     (src/doge/interfaces/api/main.py)
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
