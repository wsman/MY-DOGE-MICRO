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
| `MOONSHOT_API_KEY` | Optional live Kimi/Moonshot key |
| `DOGE_SECRET_PROVIDER` | Secret provider mode for enterprise validation paths |

Committed config files must contain placeholders only. The string
`REPLACE_WITH_DEEPSEEK_API_KEY` is intentional and must not be replaced in git.

Detailed first-run guidance remains in [../GETTING_STARTED.md](../GETTING_STARTED.md).
Operational handling remains in [../operations-runbook.md](../operations-runbook.md).
