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

## Experimental Feature Flags

All migration flags default to off unless an operator explicitly enables them.

| Variable | Meaning |
|----------|---------|
| `DOGE_FEATURE_SLOT_PLATFORM` | Enables experimental built-in slot registration and slot discovery surfaces. |
| `DOGE_FEATURE_SLOT_GOVERNANCE` | Enables experimental governance slot contribution resolution for slot-aware tool-registry entitlement composition. Requires `DOGE_FEATURE_SLOT_PLATFORM=1` for live slot resolution. |
| `DOGE_FEATURE_SLOT_WATCHER` | Enables experimental watcher slot contribution resolution for runtime event middleware. Requires `DOGE_FEATURE_SLOT_PLATFORM=1` for live slot resolution. |
| `DOGE_FEATURE_SLOT_UI` | Enables experimental UI panel slot contribution resolution and read-only `/v1/ui-panels` discovery. Requires `DOGE_FEATURE_SLOT_PLATFORM=1` for live slot resolution. |
| `DOGE_FEATURE_SLOT_ENFORCEMENT` | Enables experimental SlotKernel permission and active-health enforcement. Requires `DOGE_FEATURE_SLOT_PLATFORM=1` for live slot resolution. |
| `DOGE_FEATURE_SLOT_LOADER` | Enables experimental JSON disk manifest loading from `DOGE_SLOT_MANIFEST_DIRS` and process-local slot bundle activation. Requires `DOGE_FEATURE_SLOT_PLATFORM=1` for live activation. |
| `DOGE_FEATURE_SLOT_INSTALL` | Enables experimental manifest-only local third-party slot install preview. Requires `DOGE_FEATURE_SLOT_PLATFORM=1` and `DOGE_FEATURE_SLOT_LOADER=1`. |
| `DOGE_FEATURE_WORKFLOW_TEMPLATES` | Enables experimental workflow-template platform APIs and, with slot platform enabled, the workflow template slot consumer. |
| `DOGE_FEATURE_CAPABILITY_REGISTRY` | Enables experimental capability discovery APIs. |
| `DOGE_FEATURE_PYTHON_ANALYSIS_ENABLED` | Enables the high-risk Python analysis feature only when paired with a non-disabled executor. |

## Slot Platform Install Preview

| Variable | Meaning |
|----------|---------|
| `DOGE_SLOT_MANIFEST_DIRS` | CSV list of JSON manifest files or directories loaded as manifest-only slots when `DOGE_FEATURE_SLOT_LOADER=1`. |
| `DOGE_SLOT_INSTALL_DIR` | Local directory where `doge slots install` copies validated manifest-only slot previews. |
| `DOGE_SLOT_ENTERPRISE_ALLOWLIST` | CSV slot-id allowlist required for install preview in `DOGE_AUTH_MODE=enterprise`. |
| `DOGE_SLOT_TRUSTED_SIGNERS` | CSV signer names accepted by sidecar signature metadata verification. |
| `DOGE_SLOT_ALLOW_UNSIGNED_LOCAL` | Allows unsigned local-demo manifest installs when true; enterprise mode still requires allowlist and trusted signature metadata. |

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
