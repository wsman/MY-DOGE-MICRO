# Architecture Control Manifest

> **Manifest Version**: 2026-06-23
> **Owner**: lead-programmer (architecture); enforced by `/architecture-review`, `/gate-check`, `/story-readiness`, `/story-done`, and CI.
> **Scope**: MY-DOGE-MICRO — local-first quantitative investment decision-support platform. This manifest is the project's control-plane reference: the quality gates, the BLOCKING vs ADVISORY evidence rules, the ADR lifecycle, the registry-write policy, the forbidden patterns, and the exact verification commands.
> **How to use**: stories embed this manifest version in their header (`Control Manifest: 2026-06-21`); `/story-done` checks for staleness against this file's header. When a rule changes, bump the version date and re-review open stories.

---

## 1. The Layer Contract (what each layer may and may not do)

From ADR-0001 + `clean-architecture-migration.md §4.3`. This is the invariant every change must preserve.

| Layer | MAY import | MAY NOT import |
|---|---|---|
| `src/doge/interfaces/*` (MCP, FastAPI, CLI, GUI, Web) | `core.services`, `config` (for DI wiring) | `sqlite3`, `duckdb`, `ai_analysis`, `micro`, `macro`, `sys.path` mutation |
| `src/doge/core/services/*` | `core.ports`, `core.domain` | `sqlite3`, `duckdb`, `infrastructure`, any framework (`fastapi`, `mcp`, `PyQt6`) |
| `src/doge/core/ports/*` | stdlib, `core.domain` (optional) | any infrastructure, any framework |
| `src/doge/infrastructure/*` | `core.ports` (to implement), `config`, drivers (`sqlite3`, `duckdb`, `opentdx`, `yfinance`, `openai`) | `core.services`, `interfaces` |
| `src/doge/config/*` | stdlib only | any other layer |

**Dependency direction**: interfaces → services → ports ← infrastructure. Never point inward. The four view-backed services now depend on `IMarketViewRepository`; `src/doge/core/services/composition.py` is the single wiring site that imports the DuckDB adapter (ADR-0010 / TR-041).

### Required

- Every public method has a doc comment (coding-standards.md).
- Every system/module with non-trivial behavior has a CDD in `design/cdd/` and a governing ADR (Accepted, or explicitly Proposed with stated gating work) in `docs/architecture/`.
- All DB/network access lives behind ports; interfaces depend on services, never on drivers.
- Dependencies are injected at the wiring boundary; adapters accept their config via constructor.
- Tests are deterministic, isolated, and network-free (mocks/fakes/fixtures).
- Commits reference a design doc or task ID (coding-standards.md).

### Bounded Context Transition Rules

From ADR-0021 + ADR-0022. These rules govern the transition from the old
20-entry mixed module list to the eight bounded-context model.

| Boundary | Rule |
|---|---|
| `src/doge/products/*` | Product contexts may not directly import one another. Cross-product work goes through public capability contracts or application services. |
| `src/doge/platform/runtime/*` | Runtime coordination may not directly import product packages. It calls model, tool, artifact, eval, and capability ports. |
| `src/doge/entrypoints/*` and `src/doge/interfaces/*` | Entrypoints may call application services and bootstrap wiring, but must not open persistence adapters directly. |
| `src/doge/adapters/*` and `src/doge/infrastructure/*` | Adapters implement ports and must not contain business decisions, approval policy, research semantics, or product orchestration. |
| `src/doge/bootstrap/*` and composition roots | Only bootstrap/composition roots may wire product contexts, platform services, and concrete adapters together. |
| `src/doge/shared/*` | Shared code is limited to primitives such as config, errors, ids, clock, and contracts. It must not grow product workflow logic. |

#### Compatibility and Deprecation Rules

- Physical source moves are blocked until ADR-0022 is accepted or a story
  explicitly declares it is operating under Proposed ADR gates.
- New target packages start as shallow facades and compatibility exports; they
  must not duplicate full four-layer directory trees inside each module.
- Every deprecated public import path must identify the replacement path and
  the removal phase or version.
- Old and new imports must be covered by compatibility tests before a public
  symbol is moved.
- Feature flags created for migration must name their removal condition. A
  flag may not become a permanent second product architecture. Platformization
  flags must carry lifecycle metadata with env var, current default, target
  default-on phase, target removal phase, regression commands, and rollback
  criterion.
- TR identifiers remain flat and permanent. Never renumber TRs during bounded
  context consolidation.

---

## 2. Forbidden Patterns (architectural anti-patterns)

From ADR-0001 + `clean-architecture-migration.md §4.4` + `standards/technical-preferences.md`. These are lint/invariant rules. A PR introducing any of these into `src/doge/**` or into a *new* module fails review.

| Pattern | Definition | Where it is forbidden |
|---|---|---|
| `direct_sqlite_import_in_interface` | `import sqlite3` / `sqlite3.connect` in an interface layer | `src/api/**`, `src/doge/interfaces/**`, `src/interface/**`, MCP server, web backend |
| `direct_duckdb_connect_in_interface` | `duckdb.connect` / `connect_duckdb()` in an interface layer | same |
| `sys_path_insert` | `sys.path.insert` / `sys.path.append` bootstrapping | any module under `src/**`, any new runtime entrypoint, and `doge_mcp.py` |
| `_PROJECT_ROOT_recalculation` | `Path(__file__).resolve().parents[N]` / `os.path.dirname(...)` chains to derive the project root | anywhere except `src/doge/config/settings.py:15` |
| `cross_layer_state_write` | interface/framework modules writing shared module-level DB state; mutating process-global env (`HTTP_PROXY`, `OPENBLAS_NUM_THREADS`) from impl modules | any layer |
| hardcoded secrets / credentials / model ids / package versions in implementation modules | secrets, API keys, provider URLs, timeouts in `.py` impl files | everywhere (must live in `settings.py` or `models_config.json` + env override) |
| scattered `sys.path.insert` bootstrapping | — | everywhere (ADR-0001) |
| interface/API layers directly opening SQLite or DuckDB connections | — | everywhere (ADR-0001) |
| cross-layer imports that bypass ports/services | — | everywhere (ADR-0001) |
| network-dependent tests without isolation/fixtures | — | `tests/**` |

**Legacy tolerance**: legacy modules under `src/micro`, `src/macro`, `src/ai_analysis`, and `src/interface` may still contain documented brownfield offenders (`src/api` was migrated to clean-tree patterns — §6 grep gate green since Sprint 004). Root `mcp_server.py` has been retired and `doge_mcp.py` is not a compatibility shim. Legacy offenders receive **no new** architectural coupling, and each retired offender is struck through in the CDD's offender list.

---

## 3. Quality Gates — BLOCKING vs ADVISORY Evidence

From `standards/coding-standards.md` "Test Evidence by Story Type" table. A story cannot be marked Done while any BLOCKING gate is unmet; ADVISORY gates surface as notes but do not block.

| Story Type | Required Evidence | Location | Gate |
|---|---|---|---|
| **Logic** (formulas, AI, state machines) — e.g. RSRS | Automated unit test — must pass | `tests/unit/[system]/` or `tests/test_*.py` | **BLOCKING** |
| **Integration** (multi-system) | Integration test OR documented playtest | `tests/integration/[system]/` or `tests/test_*.py` | **BLOCKING** |
| **API Contract** (FastAPI endpoints, MCP tools) | Contract or integration test + schema diff review | `tests/contract/` or `tests/test_api_routers.py` / `tests/test_mcp_tools.py` | **BLOCKING** |
| **CLI Workflow** (commands, flags) | Argument, stdout/stderr, and exit-code tests | `tests/cli/` | **BLOCKING** |
| **Migration / Data Pipeline** (DB schema, retention) | Apply/rollback or dry-run verification with fixtures | `tests/migration/` or `tests/data/` | **BLOCKING** |
| **Web/App Workflow** (critical Vue paths) | E2E or interaction evidence + accessibility check | `tests/e2e/` or `production/qa/evidence/` | **BLOCKING** |
| Visual / Feel (chart rendering, animation) | Screenshot + lead sign-off | `production/qa/evidence/` | ADVISORY |
| UI (menus, HUD, screens) | Manual walkthrough doc OR interaction test | `production/qa/evidence/` | ADVISORY |
| Config / Data (tuning, registry) | Smoke check pass | `production/qa/smoke-[date].md` | ADVISORY |

### Determinism / isolation rules (BLOCKING for every automated test)

- **Naming**: `[system]_[feature]_test.[ext]` for files; `test_[scenario]_[expected]` for functions.
- **Determinism**: same result every run — no random seeds, no time-dependent assertions.
- **Isolation**: each test sets up and tears down its own state; no cross-test order dependency.
- **No hardcoded data**: fixtures use constant files or factory functions (exception: boundary-value tests where the exact number IS the point).
- **Independence**: unit tests do not call external APIs, databases, or file I/O — use dependency injection (e.g. `tests/test_yfinance_adapter.py` injects `FakeYFinance`; `tests/test_macro_strategist.py` injects `MagicMock`).

### CI gate (from coding-standards.md CI/CD Rules)

- The automated suite runs on every push to `main` and every PR.
- **No merge if tests fail** — tests are a blocking gate in CI.
- **Never disable or skip failing tests to make CI pass** — fix the underlying issue.

---

## 4. ADR Lifecycle

From `docs/CLAUDE.md` (Architecture Decision Records). Status transitions are mandatory and ordered.

```
Proposed  ──►  Accepted  ──►  Superseded
   │              │
   │              └─ (a Superseded ADR points to its replacement)
   └─ (Never skip Accepted. Stories referencing a Proposed ADR are auto-blocked.)
```

### Rules

1. **Proposed → Accepted**: an ADR moves to Accepted only after its gating validation criteria are met (see each ADR's "Validation Criteria" section). `/architecture-decision` Phase 5 records the transition.
2. **Never skip Accepted.** A story that references a Proposed ADR for a binding contract is **auto-blocked** by `/story-readiness` and `/create-stories`.
3. **Accepted → Superseded**: when a decision is replaced, mark it `Superseded` and point to the new ADR. Never edit an Accepted ADR in place to reverse its decision — supersede it.
4. **Each ADR must record**: Title, Status, Date, Last Verified, Decision Makers, Context (Problem/Current State/Constraints/Requirements), Decision, Alternatives Considered, Consequences, ADR Dependencies, Engine/Stack Compatibility, CDD Requirements Addressed.
5. **Run `/architecture-review` after completing a set of ADRs** — it cross-checks consistency, populates the TR registry, and produces the traceability narrative.

### Current status inventory (2026-06-23)

| ADR | Status | Note |
|---|---|---|
| 0001 Brownfield Clean Architecture Migration | **Accepted** | Foundational. |
| 0002 Centralized Runtime Configuration | **Accepted** | Settings singleton, env defaults, and tests are implemented. |
| 0003 Storage Repository Contract | **Accepted** | StorageWriteError and retention gates are met. |
| 0004 Data Source Adapter Contract | **Accepted** | TDX adapter implemented (S004-004); tdx_downloader.py thin-wrapped; _retry.py extraction deferred to a follow-on. |
| 0005 LLM Client Strategy | **Accepted** | Strategy frozen; key handling moved to env. |
| 0006 MCP Transport Strategy | **Accepted** | 77 transport tests green. |
| 0007 API Surface and CORS | **Accepted** | Strengthened-loopback-guarantee (S004-005/008b); error envelope shipped; allow_origins=['*'] safe under the loopback bind. |
| 0008 Vue Web Console Architecture | **Accepted** | Build-green, reverse-documented. |
| 0009 Cache/Metadata Port Split | **Accepted** | Port split realized; real yfinance metadata adapter is follow-on implementation work. |
| 0010 View-Service Port Injection | **Accepted** | IMarketViewRepository and composition-root wiring are implemented and tested. |
| 0011 Agent Runtime Levels | **Accepted** | Level 1/2/3 runtime model accepted; maturity claims remain governed by `docs/progress/runtime-maturity.yaml`. |
| 0012 Enterprise Model Gateway | **Accepted** | Model routing boundary accepted; live Kimi gates remain external runtime/product gates. |
| 0013 Tool Governance | **Accepted** | Tool entitlement, approval, and high-risk categories accepted. |
| 0014 Multimodal Evidence | **Accepted** | Evidence/citation provenance boundary accepted. |
| 0015 Enterprise Identity And Access | **Proposed** | OIDC/JWT, tenant ACL, approval actor, audit actor, and secrets gates remain open. |
| 0016 User-Level Objects | **Proposed** | Feature-flagged platform object slices exist; independent acceptance evidence remains open. |
| 0017 Run Summary Citation API | **Proposed** | Query API slices exist; citation/eval promotion evidence remains open. |
| 0018 Workflow Template System | **Proposed** | Template slices exist; execution and preflight gates remain open. |
| 0019 Capability Registry | **Proposed** | Registry slices exist; dependency validation and production-readiness semantics remain gated. |
| 0020 Platform Shell UI | **Proposed** | Shell slices exist; navigation/accessibility promotion gates remain open. |
| 0021 Bounded Context Consolidation | **Accepted** | Eight-context consolidation accepted by `docs/archive/audits/adr-0021-0022-review-2026-06-23.md`; external gates still block maturity promotion. |
| 0022 Directory Restructuring | **Accepted** | Facade-first target layout accepted by `docs/archive/audits/adr-0021-0022-review-2026-06-23.md`; broad physical moves remain story-gated. |

---

## 5. Registry-Write Policy

The two registries are the project's machine-readable authority. Writing them is a **separate BLOCKING approval step** from CDD/ADR authoring.

### `docs/registry/architecture.yaml` — cross-ADR architectural stances

- **Written by**: `/architecture-decision` Phase 5 (after an ADR is Accepted).
- **Read by**: `/architecture-decision` (Step 2 — before authoring), `/architecture-review` (Phase 4 — cross-ADR conflict baseline), `/create-stories`, `/dev-story`.
- **Scope**: cross-ADR stances ONLY — state ownership, interface contracts, performance budgets, API decisions, forbidden patterns. *Not* concrete runtime values (paths, ports, thresholds).
- **Rule**: never delete — set `status: superseded_by: ADR-NNNN`. When a stance changes, update the entry, set `revised:` to today, add a comment with the old value, and run `/architecture-review` to find invalidated ADRs.

### `docs/registry/entities.yaml` — (does not yet exist — see note)

- **Proposed scope**: concrete runtime constants — DB tables/schemas, env-var defaults, RSRS knobs, TDX record formats, retry budgets. Every CDD §4.7 proposes entries for this file.
- **Status**: **does not exist yet.** Its creation is itself a registry-design decision that should get its own ADR before any Phase-5 write (see traceability FINDING-5). Until it exists, value-constant proposals stay enumerated in CDD §4.7 sections only.

### `docs/architecture/tr-registry.yaml` — stable requirement IDs

- **Written by**: `/architecture-review` (appends new entries; never overwrites or renumbers).
- **Read by**: `/create-stories` (embeds TR-IDs), `/story-readiness` (validates TR-ID exists + active), `/story-done` (looks up current requirement text).
- **Rule**: IDs are **PERMANENT**. Never renumber, never delete (use `status: deprecated`). When rewording (same intent), update the `requirement` text and add a `revised` date — the ID stays. When split/replaced, set `status: superseded-by: TR-NNN`. Add new entries only at the END.

---

## 6. Verification Commands

Run these before marking any architecture-affecting story Done. The exact commands for this Product project (Python + Vue).

### Python (backend / domain / MCP / API / DB)

```bash
# Full suite (MCP tools, transport, database, repositories, adapters, strategist, notes, scanner, settings)
python -m pytest -q

# Targeted suites cited by TRs
python -m pytest tests/test_settings.py -q              # TR-001..TR-004, TR-039
python -m pytest tests/test_database.py -q              # TR-005..TR-008, TR-040
python -m pytest tests/test_yfinance_adapter.py -q      # TR-009..TR-012
python -m pytest tests/test_macro_strategist.py -q      # TR-013..TR-016
python -m pytest tests/test_momentum_scanner.py -q      # TR-017..TR-019
python -m pytest tests/test_notes_crud.py -q            # TR-022..TR-024
python -m pytest tests/test_mcp_tools.py tests/test_transport.py -q   # TR-025..TR-028
python -m pytest tests/test_api_routers.py -q           # TR-029..TR-032
python -m pytest tests/test_mcp_notes_softdelete.py -q  # TR-027
python -m pytest tests/test_pyqt_smoke.py -q            # TR-033, TR-034 (smoke — may require a display)
```

**MCP startup smoke** (manual — requires the runtime, advisory):
```bash
python doge_mcp.py --transport stdio --log-level INFO        # stdio (Claude Code path)
python doge_mcp.py --transport sse --host 127.0.0.1 --port 8902   # SSE (web console path)
```

### Web (Vue 3 + Vite 8)

From the `web/` directory:
```bash
npm run build     # vue-tsc -b && vite build  (typecheck + production build) — TR-035
npm test          # vitest smoke suite (useFuzzySearch, useVirtualScroll, scanner store) — TR-036
```

### Layer-rule grep gates (BLOCKING for interface/core layer stories)

```bash
# No direct DB drivers in interface layers
grep -rnE "import sqlite3|import duckdb|sqlite3\.connect|duckdb\.connect" \
    src/api src/doge/interfaces src/interface   # must return ZERO hits

# No project-root recalculation outside settings.py:15
grep -rnE "_PROJECT_ROOT|parents\[3\]|parents\[2\]" src/doge/   # must return exactly one line: settings.py:15

# No sys.path.insert in the clean-architecture tree or canonical MCP entrypoint
grep -rn "sys.path.insert" src/doge/ doge_mcp.py                # must return ZERO hits
```

### Stack-version consistency (advisory — run when bumping a dependency)

```bash
# Confirm the pinned versions agree across the three sources
grep -iE "fastapi|uvicorn|pydantic|mcp|duckdb|yfinance|openai|sse-starlette|pytest" requirements.txt
diff <(awk '/^## /{f=0} /Runtime|Backend and Product|Data and Market/{f=1} f' docs/reference/python/VERSION.md) \
     <(grep -iE "fastapi|uvicorn|pydantic|mcp|duckdb|yfinance|openai" requirements.txt)
```

### Governance and bounded-context checks

```bash
python -m pytest tests/unit/governance/test_s017_planning_docs.py -q
python -m pytest tests/unit/governance/test_adr_lifecycle_status.py -q
python -m pytest tests/unit/layer_gates/ -q
```

---

## 7. Brownfield-Migration Gate Sequencing

The migration is incremental (ADR-0001). Legacy entrypoints stay live until replacement paths pass tests. The six batches (from `clean-architecture-migration.md §3.3`):

| Batch | Scope | Gate to start the next batch |
|---|---|---|
| 1 | `pyproject.toml` editable install; `settings.py`; eliminate `sys.path.insert` | TR-001 grep gate passes; AC-1 (no new `sys.path.insert` under `src/doge/`) |
| 2 | Repository ports + DuckDB/SQLite adapters + repositories | TR-005, TR-008 (DB port contract + PK) |
| 3 | TDX data-source adapter (replace stub) | TR-011 (TDX no longer raises NotImplementedError) |
| 4 | Core services (view-backed services routed through `IMarketViewRepository`) | TR-041 |
| 5 | Interface rewire (API/CLI/GUI routed through services) | TR-031 + AC-6 (routers obtain data via injected services) |
| 6 | Cleanup + full test pass; delete remaining legacy compat | AC-8 (`ai_analysis/__init__.py` reduced to a re-export shim or deleted) |

**MCP entrypoint status**: `doge_mcp.py` is the canonical repo-root MCP entrypoint for stdio and SSE. The legacy `mcp_server.py` monolith was deleted after modular parity was verified; no layer-gate carve-out remains for root entrypoints.

**Rollback plan** (ADR-0001): if a migrated service breaks a workflow, route that interface back to the legacy implementation while the service contract is fixed. Legacy entrypoints remain installed until the replacement passes tests.

---

## 8. Change-Control Checklist (for any architecture-affecting PR)

- [ ] The change preserves the layer contract (§1) — no inward-pointing dependency introduced.
- [ ] No forbidden pattern (§2) is introduced into `src/doge/**` or a new module.
- [ ] The affected CDD's acceptance criteria are still satisfiable (or the CDD is updated via a CDD authoring pass, not a silent edit).
- [ ] If the change touches a `Proposed` ADR's decision, the ADR is moved to Accepted (or a new ADR is created) — never edit a Proposed/Accepted ADR in place to reverse its decision.
- [ ] If a TR-requirement text is reworded, the TR's `revised` date is set (never renumbered).
- [ ] BLOCKING evidence (§3) for the story type is present and green.
- [ ] Verification commands (§6) run clean on the target platform (Windows 10 LTSC is first-class).
- [ ] Commits reference the relevant design doc or task ID.

---

*Manifest Version 2026-06-23. Re-review and bump this date whenever a rule, gate, ADR status, or verification command changes.*
