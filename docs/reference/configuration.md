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

Five local Slot Platform flags now default on for the controlled built-in path:
`DOGE_FEATURE_SLOT_PLATFORM`, `DOGE_FEATURE_SLOT_GOVERNANCE`,
`DOGE_FEATURE_SLOT_WATCHER`, `DOGE_FEATURE_WORKFLOW_TEMPLATES`, and
`DOGE_FEATURE_SLOT_LOADER`. Operators can opt out with `=0` / `false`.
Higher-risk install, enforcement, runtime interception, UI-slot, and execution
surfaces remain default off.

| Variable | Default | Meaning |
|----------|---------|---------|
| `DOGE_FEATURE_SLOT_PLATFORM` | on | Enables experimental built-in slot registration and slot discovery surfaces. Set `0` to restore legacy direct wiring. |
| `DOGE_FEATURE_SLOT_GOVERNANCE` | on | Enables governance slot contribution resolution for slot-aware tool-registry entitlement composition. Requires Slot Platform to remain enabled; set this flag to `0` for governance-only opt-out. |
| `DOGE_FEATURE_SLOT_WATCHER` | on | Enables watcher slot contribution resolution for runtime event middleware. Requires Slot Platform to remain enabled; set this flag to `0` for watcher-only opt-out. |
| `DOGE_FEATURE_WORKFLOW_TEMPLATES` | on | Enables workflow-template platform APIs and, with slot platform enabled, the workflow template slot consumer. |
| `DOGE_FEATURE_SLOT_LOADER` | on | Enables JSON disk manifest loading from `DOGE_SLOT_MANIFEST_DIRS` as manifest-only slots and persisted local bundle activation/deactivation. Requires `DOGE_FEATURE_SLOT_PLATFORM=1` for live activation; set `0` to disable loader and activation surfaces. |
| `DOGE_FEATURE_SLOT_UI` | off | Enables experimental UI panel slot contribution resolution and read-only `/v1/ui-panels` discovery. Requires `DOGE_FEATURE_SLOT_PLATFORM=1` for live slot resolution. |
| `DOGE_FEATURE_SLOT_ENFORCEMENT` | off | Enables experimental SlotKernel permission and active-health enforcement. Requires `DOGE_FEATURE_SLOT_PLATFORM=1` for live slot resolution. |
| `DOGE_FEATURE_SLOT_RUNTIME_INTERCEPTION` | off | Enables experimental in-process runtime guards for built-in slot db/secret/network port access. Requires slot-aware execution paths; does not provide filesystem mediation or OS/container/WASM isolation. |
| `DOGE_FEATURE_SLOT_INSTALL` | off | Enables experimental manifest-only local third-party slot install preview. Requires `DOGE_FEATURE_SLOT_PLATFORM=1` and `DOGE_FEATURE_SLOT_LOADER=1`. |
| `DOGE_FEATURE_CAPABILITY_REGISTRY` | off | Enables experimental capability discovery APIs. |
| `DOGE_FEATURE_PYTHON_ANALYSIS_ENABLED` | off | Enables the high-risk Python analysis feature only when paired with a non-disabled executor. |

`DOGE_FEATURE_SLOT_ENFORCEMENT` and
`DOGE_FEATURE_SLOT_RUNTIME_INTERCEPTION` are intentionally separate.
Enforcement is SlotKernel admission policy before contribution resolve/start.
Runtime interception is P4 in-process mediation for guarded db/secret/network
ports after a built-in slot call is executing. Runtime interception is not a
malicious-code boundary: direct filesystem, socket, sqlite, or process access
outside guarded ports remains P5 sandbox work. The Python analysis subprocess is
also hardened with secret env scrub and a scratch cwd, but Windows remains a
soft boundary without rlimit/seccomp/chroot-style isolation.

## Slot Platform Install Preview

| Variable | Meaning |
|----------|---------|
| `DOGE_SLOT_MANIFEST_DIRS` | CSV list of JSON manifest files or directories loaded as manifest-only slots when `DOGE_FEATURE_SLOT_LOADER=1`. |
| `DOGE_SLOT_INSTALL_DIR` | Local directory where `doge slots install` copies validated manifest-only slot previews. |
| `DOGE_SLOT_ENTERPRISE_ALLOWLIST` | CSV slot-id allowlist required for install preview in `DOGE_AUTH_MODE=enterprise`. |
| `DOGE_SLOT_TRUSTED_PUBLISHER_KEYS` | CSV `key_id=base64_ed25519_public_key` pairs trusted for v2 `slot.signature.json` Ed25519 manifest signatures. |
| `DOGE_SLOT_TRUSTED_SIGNERS` | Deprecated legacy v1 metadata signer names. Kept only so old sidecars can be reported as `legacy`; enterprise install requires verified v2 signatures. |
| `DOGE_SLOT_ALLOW_UNSIGNED_LOCAL` | Allows unsigned local-demo manifest installs when true; enterprise mode still requires allowlist and verified v2 Ed25519 signature. |

`DOGE_SLOT_TRUSTED_PUBLISHER_KEYS` may also be supplied through the canonical
secret name `slot.trusted_publisher_keys` when `DOGE_SECRET_PROVIDER=process`.
The secret value uses the same CSV pair format as the environment variable.

Slot signing-key revocations are stored in the local agent database table
`slot_signer_revocations` and are managed by `doge slots revoke-key`. There is
no separate revocation environment variable.

v2 sidecars are Ed25519 signatures over canonical SlotManifest JSON bytes. v1
sidecars from Sprint 047 remain readable as `legacy` but are not cryptographic
and do not satisfy enterprise verified-signature policy.

## Enterprise ACL Resource Types

Enterprise HTTP slot-bundle activation and deactivation use database ACL grants,
not `DOGE_SLOT_ENTERPRISE_ALLOWLIST`. Grant `resource_type=slot_bundle`,
`resource_id=<bundle id>` or `*`, and `permission=write` or `*` in
`enterprise_acl_grants` to authorize `POST /v1/slot-bundles/{bundle_id}/activate`
and `POST /v1/slot-bundles/active/deactivate`.

`DOGE_SLOT_ENTERPRISE_ALLOWLIST` remains scoped to the manifest-only install
preview path.

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
