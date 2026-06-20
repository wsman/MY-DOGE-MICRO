# ADR-0002: Centralized Runtime Configuration

## Status

Accepted

## Date

2026-06-11

## Last Verified

2026-06-12

## Decision Makers

WSMAN, python-specialist

## Summary

MY-DOGE-MICRO's legacy code recomputes `_PROJECT_ROOT` and inserts into `sys.path` independently in ~20 modules under `src/micro/`, `src/macro/`, `src/doge/interfaces/api/routers/`, `src/interface/`, and `src/ai_analysis/`. This ADR decides that all runtime paths, environment overrides, database locations, TDX endpoints, market constants, and MCP transport settings are owned by a single frozen-dataclass configuration module — `src/doge/config/settings.py` — exposed through the `get_settings()` lazy singleton, and that no new code may recalculate the project root or hardcode paths.

## Engine Compatibility

| Field | Value |
|-------|-------|
| **Engine** | Python 3.10+ |
| **Domain** | Core / Configuration / Runtime |
| **Knowledge Risk** | LOW — `dataclasses`, `pathlib`, `os.environ` are stable stdlib APIs in training data |
| **References Consulted** | `docs/reference/python/VERSION.md`, `src/doge/config/settings.py`, `docs/architecture/adr-0001-brownfield-clean-architecture.md`, `docs/MCP_SERVER.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | Run `pytest tests/test_settings.py` (to be added) and confirm no `sys.path.insert` / `_PROJECT_ROOT` recalculation in `src/doge/**` |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0001 (Brownfield Clean Architecture Migration) — must be Accepted; this ADR operationalizes its `sys_path_insert` and `_PROJECT_ROOT_recalculation` forbidden patterns |
| **Enables** | Module CDDs for `market-data-storage` (#2), `data-sources` (#3), `mcp-server` (#8), `fastapi-service` (#9); the `clean-architecture-migration` (#12) backlog |
| **Blocks** | New Foundation/Core/Interface modules may not introduce their own root/path resolution until they consume `get_settings()` |
| **Ordering Note** | This ADR documents an already-implemented module (`settings.py` exists and is consumed by `src/doge/**`); the migration of legacy consumers is sequenced by #12, not by this ADR |

## Context

### Problem Statement

The brownfield source tree calculates the project root and resolves database/data paths in a dozen different ways: `os.path.dirname` chains of depth 2, 3, and 4, `Path(__file__).resolve().parents[N]` with N=2 or 3, and per-file `sys.path.insert(0, ...)` bootstrapping. The same five `DOGE_*` environment variables are read in at least two places (`src/doge/config/settings.py` and `src/ai_analysis/__init__.py`) with duplicated helper code. This produces:

- Path drift when the tree is restructured or files are moved between packages.
- Silent disagreement between modules about where data lives.
- Brittle imports that fail in test contexts and alternative launchers (MCP stdio vs SSE vs FastAPI uvicorn vs PyQt entry).
- An un-testable configuration surface (no single seam to inject test paths).

The cost of not deciding is that every new module reinvents path resolution, deepening the debt that ADR-0001's migration must later unwind.

### Current State

- A centralized module already exists: `src/doge/config/settings.py` (frozen dataclasses `Settings`/`DBConfig`/`TDXConfig`/`MarketConfig`/`MCPConfig`, lazy `get_settings()`, `reset_settings()` test helper, single `_PROJECT_ROOT` at `settings.py:15`).
- Clean-architecture code under `src/doge/**` already imports exclusively from `doge.config` (server.py, infrastructure/database/*, infrastructure/cache/*).
- Legacy modules still recalculate roots: `src/micro/{tdx_downloader,market_scanner,momentum_scanner,industry_analyzer,database}.py`, all `src/doge/interfaces/api/routers/*.py`, `src/macro/config.py`, `src/cli.py`, `src/interface/{scanner_gui,dashboard,analysis_gui}.py`, and `src/ai_analysis/__init__.py` (which duplicates the env-reading helper).
- Environment vars honored: `DOGE_DB_DIR`, `DOGE_CN_DB`, `DOGE_US_DB`, `DOGE_RESEARCH_DB`, `DOGE_DUCKDB_PATH` (documented in `docs/MCP_SERVER.md:386-389`).
- Process-global BLAS thread shims (`OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`) are set in three separate modules, not in settings.
- LLM/model configuration (`DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL`, `models_config.json`) lives entirely in `src/macro/config.py`, outside this centralization.

### Constraints

- **Local-first**: configuration must remain overridable via plain environment variables (no external secrets manager, no cloud config service).
- **No breaking change to existing operators**: defaults must keep pointing at `<project_root>/data` so unconfigured runs behave identically.
- **Testability**: tests must be able to point the system at a temp data dir deterministically (Section 8 acceptance gate).
- **Immutability**: configuration must be effectively immutable after construction so cached paths cannot drift mid-process.
- **Stdlib-only for the configuration core**: avoid pulling a config library (pydantic-settings, dynaconf) into the Foundation layer that everything else depends on.

### Requirements

- A single, documented source of truth for `PROJECT_ROOT`.
- A single reader of each `DOGE_*` env var.
- Immutable settings objects.
- Overridable database paths via env vars, with documented defaults and operational risk per knob.
- A reset seam for tests.
- A migration path (owned by #12) to retire every legacy root recalculation without breaking working entrypoints.

## Decision

Adopt `src/doge/config/settings.py` as the sole runtime-configuration module for paths, database locations, TDX constants, market constants, and MCP transport settings.

1. **Single root source**: `PROJECT_ROOT` is computed exactly once at `src/doge/config/settings.py:15` as `Path(__file__).resolve().parents[3]`. No other module may recompute it.
2. **Single env reader**: the `_env_path(name, default)` helper (`settings.py:18-20`) is the only function that reads `DOGE_*` env vars. `src/ai_analysis/__init__.py`'s duplicate must be retired (migration task for #12).
3. **Frozen dataclasses**: `Settings` and all nested configs are `@dataclass(frozen=True)`. Derived DB paths are set in `__post_init__` via `object.__setattr__` so the public API stays immutable.
4. **Lazy singleton + reset**: `get_settings()` caches one instance; `reset_settings()` clears it for tests. Tests set env vars *before* the first call, then `reset_settings()`.
5. **No validation at construction** (current state): settings accepts any path/string the env provides; existence/writability is the caller's concern. (Open question ADR-tracked: whether to add a typed `ConfigError` validation pass.)
6. **No hardcoded secrets/credentials in `settings.py`**: API keys, model selection, proxy URLs remain outside this module (owned by `src/macro/config.py` and `models_config.json`) — see Open Questions in the CDD; consolidating LLM config is deferred.
7. **Hardcoded non-env constants are permitted** in `settings.py` (TDX servers/ports, market thresholds, MCP host/port) but MUST each be documented in CDD Section 7 with default, range, and operational risk, and are proposed for the registry (CDD Section 4.7).
8. **Forbidden in any new module** (operationalizes ADR-0001 `forbidden_patterns`):
   - `sys.path.insert(...)` bootstrapping outside documented compatibility shims.
   - `Path(__file__).resolve().parents[N]` / `os.path.dirname(...)` chains to derive the project root.
   - Re-reading `DOGE_*` env vars directly instead of via `get_settings()`.
   - Hardcoding DB paths as string literals.

### Architecture

```text
            ┌──────────────────────────────────────────────┐
            │  process environment (DOGE_* env vars)        │
            └──────────────────────┬───────────────────────┘
                                   │ read once
                                   v
            ┌──────────────────────────────────────────────┐
            │  src/doge/config/settings.py                  │
            │   _PROJECT_ROOT  (single source)              │
            │   _env_path()    (single env reader)          │
            │   DBConfig / TDXConfig / MarketConfig /       │
            │   MCPConfig  (frozen dataclasses)             │
            │   get_settings() -> lazy singleton            │
            │   reset_settings() -> test seam               │
            └──────────────────────┬───────────────────────┘
                                   │ imported via
                                   v
   ┌──────────────────┬───────────┴───────────┬──────────────────┐
   v                  v                       v                  v
infrastructure/    interfaces/           core/services      (legacy modules
database/*         mcp/server.py          (read db.*,        migrate via #12;
(read db.*)        (read mcp.*, data_dir)  market.*)         then adopt get_settings)
```

### Key Interfaces

```python
# The only sanctioned public surface for runtime configuration.
# src/doge/config/__init__.py
from .settings import Settings, get_settings
__all__ = ["Settings", "get_settings"]

# src/doge/config/settings.py
def get_settings() -> Settings: ...     # lazy singleton
def reset_settings() -> None: ...        # test-only

# Consumer pattern (target for ALL modules):
from doge.config import get_settings
cn_db_path = get_settings().db.cn_db          # Path
duckdb_path = get_settings().db.duckdb        # Path
rsrs_window = get_settings().market.rsrs_window  # int
```

### Implementation Guidelines

- New modules under `src/doge/**` MUST `from doge.config import get_settings` and read paths/constants from the returned `Settings`. They MUST NOT call `Path(__file__).parents[...]` or `os.path.dirname` to derive project paths.
- New database/infrastructure adapters MUST accept their path(s) via constructor injection, defaulting to `get_settings().db.<field>` at the wiring boundary only — never inside the adapter's hot path. (Keeps the adapter unit-testable per coding standards.)
- Legacy modules are NOT to be edited piecemeal for this ADR; their retirement is sequenced by `clean-architecture-migration` (#12). Until then, they remain as documented compatibility shims.
- Tests MUST NOT mutate `os.environ` for a `DOGE_*` var after `get_settings()` has been called in the same process without first calling `reset_settings()`.
- Adding a new env-overridable path requires: (a) a field on the relevant frozen dataclass, (b) a row in CDD Section 7.1 with default/range/ownership/risk, (c) a registry proposal entry in CDD Section 4.7, and (d) a unit test.

## Alternatives Considered

### Alternative 1: pydantic-settings / dynaconf config library

- **Description**: Replace the hand-rolled dataclasses with `pydantic.BaseSettings` or `dynaconf`, gaining automatic env binding, validation, and `.env` loading.
- **Pros**: Validation, type coercion, and `.env` support for free; industry-standard.
- **Cons**: Adds a non-stdlib dependency to the Foundation layer that every other module imports; `pydantic` v2 env-binding semantics can surprise; heavier cold-import cost for MCP/CLI startup; current frozen-dataclass design already covers the local-first, env-only requirement.
- **Estimated Effort**: Medium (rewrite settings + adapt every consumer call site).
- **Rejection Reason**: Stdlib-only constraint for the configuration core; current design is sufficient for local-first single-user operation. Revisit if multi-environment profiles (Open Question #4) become a real requirement.

### Alternative 2: Keep per-module root calculation, just add a shared helper

- **Description**: Export a `project_root()` helper but allow modules to keep calling it (and keep `sys.path` manipulation).
- **Pros**: Minimal change; no migration backlog.
- **Cons**: Does not satisfy ADR-0001's forbidden patterns; `sys.path.insert` side effects remain; the helper is just another shared constant, not a configuration seam — env overrides still get duplicated.
- **Estimated Effort**: Lowest.
- **Rejection Reason**: ADR-0001 already forbids `sys_path_insert` and `_PROJECT_ROOT_recalculation`; this alternative contradicts an Accepted ADR.

### Alternative 3: Config file (YAML/TOML) instead of env vars

- **Description**: Move all settings to a `config.yaml`/`pyproject.toml` `[tool.doge]` table.
- **Pros**: Self-documenting; structured; supports nested defaults.
- **Cons**: Local-first operators currently override via shell env (`scripts/start_mcp_sse.sh`, README); a file introduces a second source of truth and a parse failure mode; does not eliminate the root-recalculation problem on its own.
- **Estimated Effort**: Medium.
- **Rejection Reason**: Env-var override is the established operator contract (documented in `docs/MCP_SERVER.md`). A config file can layer on top later (Open Question) but is not the primary mechanism.

## Consequences

### Positive

- One place to audit every path and default (CDD Section 7).
- Deterministic test seams via `reset_settings()` + env injection.
- Eliminates a whole class of "wrong root" bugs as new modules adopt `get_settings()`.
- Satisfies two of ADR-0001's forbidden patterns (`sys_path_insert`, `_PROJECT_ROOT_recalculation`) for all new code.
- Frozen dataclasses make accidental mid-process mutation impossible.

### Negative

- A migration backlog (Section 3.11 of the CDD) of ~20 legacy files must be retired by `clean-architecture-migration` (#12) — until then, two configuration worlds coexist.
- No construction-time validation means bad env values surface late (first DB write) with non-obvious errors.
- Hardcoded TDX IPs and market thresholds are not operator-tunable without a code change (registry migration will help; not yet done).
- The singleton is not thread-safe on cold construction (benign race, documented in CDD Section 5).

### Neutral

- LLM/model config (`DEEPSEEK_*`, `models_config.json`) stays in `src/macro/config.py` for now — a deliberate scope boundary, tracked as an open question.
- BLAS thread shims stay as import-time `setdefault` in the three consuming modules, not in settings.

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Legacy modules and `get_settings()` disagree on a path during the migration window | Medium | High | Migration is workflow-by-workflow with regression tests (per ADR-0001); legacy entrypoints kept until equivalent paths verified. |
| Operator sets `DOGE_DUCKDB_PATH` without the matching CN/US overrides; cross-DB views attach stale sqlite | Medium | Medium | Document in CDD Section 5 + 7.1; future validation pass (Open Question #2) could warn on partial override. |
| Silent path drift if `settings.py` is moved in the tree (the `parents[3]` math breaks) | Low | High | Add a smoke test asserting `get_settings().project_root` contains an expected sentinel (e.g. `CLAUDE.md`); pin via CDD acceptance criteria. |
| Non-ASCII / relative env paths fail on Windows | Low | Medium | Document (CDD Section 5); future `_env_path` normalization (Open Question #6). |
| A new contributor re-introduces `sys.path.insert` under pressure | Medium | Low | Code-review check against ADR-0001 forbidden patterns; `/architecture-review` gate. |

## Performance Implications

| Metric | Before (legacy per-module recalc) | Expected After (`get_settings()`) | Budget |
|--------|-----------------------------------|----------------------------------|--------|
| Cold-import config cost | N `os.path.dirname` calls per module, N `sys.path.insert` | One `Path.resolve()` + one `_env_path` per DB var, cached | <5ms added to first import; offset by removing duplicate work |
| Per-query path lookup | Each legacy call recomputes joins | Cached singleton, `Path` objects reused | Strictly faster or equal |
| Memory | One set of path strings per module | One shared frozen `Settings` instance | Lower |
| MCP startup latency | Recalculation across many import chains | Single construction | Within the 30s MCP tool budget (not on the hot path) |

## Migration Plan

This ADR's *module* already exists and is consumed by `src/doge/**`. The migration work is retiring the legacy consumers and is owned by `clean-architecture-migration` (#12). The sequence:

1. **Freeze** (done): `src/doge/config/settings.py` is the canonical implementation; documented in CDD `runtime-configuration`.
2. **Adopt in new code** (enforced): any new module under `src/doge/**` must import `get_settings()`; ADR-0001 forbidden patterns block alternatives.
3. **Retire `src/ai_analysis/__init__.py` duplicate** (next): collapse the parallel `_env_path` + `DOGE_*` reading into `get_settings()`; move its DuckDB helpers to `src/doge/infrastructure/`.
4. **Retire `src/doge/interfaces/api/routers/*.py` root recalcs** (per-router): replace each `_PROJECT_ROOT = os.path.dirname(...)x4` with `get_settings()`; keep routes behavior-identical; add router tests.
5. **Retire `src/micro/*.py` and `src/interface/*.py` root recalcs**: route through services/ports per ADR-0001; these are the largest offenders.
6. **Retire `src/macro/config.py` root recalc** and decide on LLM-config consolidation (Open Question #1).
7. **Registry migration** (Phase 5, separate blocking approval): move the constants enumerated in CDD Section 4.7 into `docs/registry/entities.yaml` / `architecture.yaml`.

**Rollback plan**: Legacy entrypoints are preserved throughout. If migrating a consumer to `get_settings()` breaks its workflow, revert that consumer to its prior root calculation while the contract is fixed; the central `settings.py` itself does not change. The ADR is not reversed unless the centralized model is fundamentally rejected, in which case the duplicated-helper approach (Alternative 2) is the fallback of last resort and would require superseding this ADR.

## Validation Criteria

- [ ] `from doge.config import get_settings` imports with no `sys.path` mutation and no exception. **[GATE]**
- [ ] `grep -rn "_PROJECT_ROOT\|parents\[3\]\|parents\[2\]" src/doge/` returns exactly one line: `src/doge/config/settings.py:15`.
- [ ] `grep -rn "sys.path.insert" src/doge/` returns zero matches.
- [ ] `tests/test_settings.py` exists and asserts: singleton identity, env override of `DOGE_CN_DB`/`DOGE_DB_DIR`, empty-string-treated-as-unset, frozen-field mutation raises, and `reset_settings()` reseeds. **[GATE]**
- [ ] Every clean-architecture DB consumer obtains paths via `get_settings()` (no `Path(__file__)` math in `src/doge/infrastructure/**` or `src/doge/interfaces/mcp/**`).
- [ ] CDD `runtime-configuration` Section 7 enumerates all five `DOGE_*` env vars with default, range, ownership, and risk.
- [ ] No `_PROJECT_ROOT` recalculation outside `settings.py` in any *new* (post-ADR) module — enforced by code review and `/architecture-review`.

## CDD Requirements Addressed

| CDD Document | System | Requirement | How This ADR Satisfies It |
|--------------|--------|-------------|---------------------------|
| `design/cdd/runtime-configuration.md` | Runtime Configuration | "single source of truth for all paths, constants and env vars" (CDD Section 1, Promise) | Establishes `settings.py` + `get_settings()` as the sole sanctioned configuration seam; forbids per-module root recalculation and duplicate env readers. |
| `design/cdd/runtime-configuration.md` | Runtime Configuration | "every env var documented with default, valid range, and ownership" (CDD Section 7) | Decision point #5/#7 requires every knob to be documented and proposed for the registry; construction-time validation deferred is an explicit, tracked non-decision. |
| `design/cdd/module-index.md` | Clean Architecture Migration | "Centralize runtime configuration and path handling" (dependency of modules #2/#3/#8/#9) | Provides the centralized target that #12 migrates legacy modules toward. |
| `docs/architecture/adr-0001-brownfield-clean-architecture.md` | Layer discipline | forbidden_patterns `sys_path_insert`, `_PROJECT_ROOT_recalculation` | This ADR operationalizes those patterns for the configuration domain and defines the acceptance grep gates. |

> Foundational dependency note: this ADR also *enables* every Foundation/Core/Interface/Presentation module CDD to reference a stable path/settings contract.

## Related

- **ADR-0001** — Brownfield Clean Architecture Migration (this ADR depends on it; operationalizes two of its forbidden patterns). `docs/architecture/adr-0001-brownfield-clean-architecture.md`
- **CDD**: `design/cdd/runtime-configuration.md` (Module #1).
- **Source truth**: `src/doge/config/settings.py`, `src/doge/config/__init__.py`.
- **Parallel implementation to retire**: `src/ai_analysis/__init__.py:21,24-36`.
- **Documented env vars**: `docs/MCP_SERVER.md:386-389`.
- **Startup scripts honoring the same env vars**: `scripts/start_mcp_sse.sh:15`, `scripts/start_mcp_sse.bat:13`.
- **Future supersession triggers**: if Open Question #2 (validation), #4 (env profiles), or #1 (LLM-config consolidation) is adopted, supersede with ADR-00NN rather than silently amending this one.
