# Configuration Reference

Runtime configuration is centralized in `src/doge/config/settings.py`, with
operator overrides supplied by environment variables.

## Core Local Paths

| Variable | Meaning |
|----------|---------|
| `DOGE_DB_DIR` | Root local data directory |
| `DOGE_CN_DB` | A-share SQLite OHLCV database |
| `DOGE_US_DB` | US-equity SQLite OHLCV database |
| `DOGE_RESEARCH_DB` | Research notes/name cache SQLite database |
| `DOGE_AGENT_DB` | Agent runtime state database |
| `DOGE_DOCUMENT_STORAGE_DIR` | Local document payload storage |
| `DOGE_DUCKDB_PATH` | DuckDB analytical file |

## Market And Runtime Knobs

| Variable | Meaning |
|----------|---------|
| `DOGE_RETENTION_DAYS` | Per-ticker OHLCV retention window |
| `MCP_HOST` | MCP SSE host |
| `MCP_PORT` | MCP SSE port |
| `MCP_TOOL_TIMEOUT` | MCP tool timeout seconds |

## Secrets

| Variable | Meaning |
|----------|---------|
| `DEEPSEEK_API_KEY` | Primary key source for DeepSeek/OpenAI-compatible macro LLM paths |
| `MOONSHOT_API_KEY` | Optional live Kimi/Moonshot key; use `sk-kimi-*` with the Kimi Coding v1 baseline |
| `DOGE_SECRET_PROVIDER` | Secret provider mode for enterprise validation paths |

## Kimi Coding Release Baseline

Kimi Coding is the v1 live Kimi standard for chat-centered capabilities:
Research Agent runs, report generation, tool/function calling, thinking mode,
and model routing.

| Variable | Meaning |
|----------|---------|
| `KIMI_CODING_MODE` | Set to `1` to use `https://api.kimi.com/coding/v1` when no explicit `KIMI_BASE_URL` is set |
| `DOGE_TEXT_LLM_PROVIDER` | `kimi-coding` also enables coding mode for text paths |
| `KIMI_BASE_URL` | Explicit OpenAI-compatible Kimi base URL; overrides coding mode |
| `KIMI_CODING_BASE_URL` | Coding endpoint URL, default `https://api.kimi.com/coding/v1` |
| `KIMI_CODING_USER_AGENT` | Default coding-agent User-Agent when coding mode is enabled |
| `KIMI_CLIENT_USER_AGENT` | Explicit User-Agent override |
| `KIMI_EXTRA_HEADERS` | JSON object merged into Kimi default headers; must not contain secrets |

The Kimi Coding endpoint does not expose `/files`. Document upload, CLI
`/attach`, and local evidence workflows remain available through local payload
storage, local parsing, SQLite evidence records, and local RAG lookup.

Committed config files must contain placeholders only. The string
`REPLACE_WITH_DEEPSEEK_API_KEY` is intentional and must not be replaced in git.

Detailed first-run guidance remains in [../guides/getting-started.md](../guides/getting-started.md).
Operational handling remains in [../operations/runbook.md](../operations/runbook.md).
