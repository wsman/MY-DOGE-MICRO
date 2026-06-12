# Active Session State

> Living checkpoint. Gitignored. Read this first after any compaction/crash.
> Branch: `cdd-adoption-2026-06-11` · Date: 2026-06-12

## Current Task

**Sprint 003 — Verification execution**
(`production/sprints/sprint-003-verification.md`, milestone `production/milestones/verification-milestone.md`).
Stage advanced Implementation → Verification under CONCERNS verdict
(`production/gate-checks/gate-implementation-verification-2026-06-12.md`).
Release-Ready v1 plan complete; now executing Verification sprint to close
high-impact CONCERNS and prepare for Verification → Release gate.

- 6 Must-Haves, 4 Should-Haves, 3 Nice-to-Haves.
- TDX adapter (S003-004) formally deferred.
- Critical path: S003-002 user-test validation — start Day 1.
- Governance: S003-014 requires a FRESH `/architecture-review` session.

## Orchestrator Decisions (adopted from recon recommendations)

| Story | Decision |
|---|---|
| S002-001 RSRS sign | **zero→+1** (option A); ADR-0001 note, no new ADR |
| S002-002 macro guards | add flat-variance + NaN guards; adopt zero→+1 |
| S002-003 cache/metadata port | **SPLIT** → ITickerNameCache + new ITickerMetadataSource; ADR-0009 Proposed |
| S002-004 view-service port | **INJECT-PORT** → new IMarketViewRepository + adapter + DI root; ADR-0010 Proposed |
| S002-005 forbidden patterns | remediate 3 named sites + all sqlite3 in scan.py; route via SQLiteConnection/Settings |
| S002-006 StorageWriteError | create class + add save_prices to IStockRepository; fix swallow in database.py + caller loops |
| S002-007 retention | **raise to 730** (option A); MarketConfig.retention_days; fix ADR-0003 365→730 |
| S002-008 config drift | **remove** scanner_filters from models_config.json; Settings().market single source |
| S002-009 error envelope | global handler; **string-enum** codes (bad_request/not_found/conflict/internal_error) |
| S002-010 SSE watchdog | 30s stall→terminal error; 0 auto-reconnect; status ref idle\|running\|error\|complete |
| S002-011 ADR promotion | promote ADR-0002 + ADR-0005 → Accepted NOW; gate-notes for 0003/0004/0007 |
| S002-012 @pretext | **vendor** 5 files (~3.2k LOC) into web/src/vendor/pretext/ |
| S002-013 key rotation | placeholder + env-primary + hard RuntimeError; drop api_key from /config; GUI requires env export |

**Operator-only step (cannot automate):** revoke + reissue the leaked DeepSeek key
in the console. **NO git history rewrite** (destructive; revocation is the real fix).
The key IS in git history (models_config.json tracked despite .gitignore:11).

## Wave 1 — COMPLETE (all 13 stories, 9 commits 61617ca→9cb71d1)

Suite: **394 passed, 1 skipped, 1 xfailed**; web build green; 49 web tests; `src/doge/` grep gate clean;
ADR-0002/0003/0005 Accepted; ADR-0004/0007/0009/0010 Proposed w/ gate-notes.

Committed stories (no co-author):
- `61617ca` S002-013 key→env (TR-015) — 15 tests; +bonus key-scrub in strategist.py
- `fc15cb2` S002-007 retention 730 (TR-006) — 17 tests incl. BLOCKING migration
- `e8077c9` S002-010 SSE watchdog (TR-036) — 14 web tests
- `c6c94aa` S002-001+002 RSRS sign unify zero→+1 + macro guards (TR-016) — 51 tests
- `d58a902` S002-003+004+006 ports split + view-service injection + StorageWriteError — 36 tests

Suite: **337 passed, 1 skipped, 1 xfailed**. `src/doge/` grep gate CLEAN (no sys.path.insert).
Key corrections found in flight: `models_config.json` is gitignored+UNTRACKED (never in git
## Wave 2 + Wave 3 — COMPLETE (commits 785d3a7, 784ed08, d9b0e6d)

**Wave 2** (785d3a7): 6 ops docs — GETTING_STARTED, API, CLI, operations-runbook, design/ux/
seeds (README + interaction-patterns + accessibility-requirements + scanner-flow), README refresh.
All cite shipped Wave-1 behavior. 463 tests.

**Wave 3a** (784ed08): `pip install -e .` activated (doge-0.1.0; src/interface/__init__.py added).
Batch-1 removed sys.path shims from 16 legacy modules (package-qualified imports via editable
install; api routers kept settings-derived _PROJECT_ROOT name for test monkeypatching). Batch-4
rewired cli.py onto the service layer (composition factories) + exit codes. 493 tests.

**Wave 3b** (d9b0e6d): Batch-5 retargeted .mcp.json + all 4 launchers + test_mcp_tools/test_transport
to the modular server (doge_mcp.py → doge.interfaces.mcp.server). Live parity probe gated it:
caught+fixed a total-breakage bug (tool names were tool_query_stock not query_stock), migrated
PID detection, fixed normalize_ticker + _fmt. stock_overview notes/sector block ported (parity).
**Batch-6 (delete mcp_server.py) DEFERRED** — agent's live probe covered 2/6 tools' output parity;
monolith retirement + test_mcp_notes_softdelete retarget deserve fresh /architecture-review.
mcp_server.py is now unreferenced dead code (safe fallback).

## Wave 4 — DONE (commit 42d3128; cleanup applied 2026-06-12)

`mcp_server.py` RETIRED, `doge_mcp.py` shim removed (sole canonical MCP entrypoint), layer-gate carve-out dropped, **ADR-0009/0010 → Accepted**, docs synced. **Fresh `/gate-check` → CONCERNS** (4/4 directors CONCERNS, 0 NOT READY); user advanced `production/stage.txt`: Implementation → **Verification** with recorded risk note (commit bc3d6e2). Report: `production/gate-checks/gate-implementation-verification-2026-06-12.md`. Remaining gaps = Verification/Sprint 003 work (user-test evidence, API router DI, TDX adapter, RSRS view fix, per-view UX specs, art bible, a11y baseline) — not yet planned.

**📋 Full checklist: `production/wave-4-review-readiness.md`** (tracking doc — pre-flight P1–P9,
gate-check readiness, architecture-review readiness, deferred-items disposition, operator steps,
fresh-session execution script). Read that file; this section is the pointer + headline.

Final state (post-Wave-4): **487 pytest passed/2 skipped/6 xfailed**, web build green, 49 web tests,
`src/` + `doge_mcp.py` sys.path gate CLEAN (0), `.mcp.json` references `mcp_server.py` ZERO times.
Wave 4 commit `42d3128` (retire monolith + promote ADR-0009/0010 + sync docs); preceded by `3916ff9`
(B1+B2 Batch-6 prerequisites), `4dafd97`/`52505ca` (readiness doc), `464127a` (review artifact),
`7457735` (code-review fixes).

Fresh-session gate actions (I cannot run these unbiased — I implemented the work):
- **Session ①** `/gate-check` — phase-gate verdict + production/stage.txt advancement.
- **Session ②** `/architecture-review` — promote ADR-0009/0010 (decisions realized, §3.1); rule on
  Batch-6 deletion (§3.2 prerequisites B1 retarget test_mcp_notes_softdelete + B2 6-tool parity
  test must land first); rule on the 3 known issues (§3.3); re-run adoption audit → 0/0/0.

Deferred items (documented; see readiness doc §4 for full disposition):
- Batch-6 monolith deletion (gated on B1+B2 above).
- Full API router DI (deps.py + data/macro/analysis/main off sqlite3.connect) — §6 src/api gate
  partially RED; API works as-is. Recommend Wave 5.
- TDX adapter migration (tdx.py NotImplementedError → real impl) — out of Sprint scope; gates
  ADR-0004 promotion + full tdx_downloader.py retirement. Recommend Wave 5.
- DuckDB vw_rsrs_ranking sign-inversion — xfail-pinned; fix needs gitignored data/views.sql edit
  + re-materialize + DDL versioning. Runbook flags it (prefer 'doge rsrs' CLI over the MCP view).
- Operator step: revoke+reissue the historically-on-disk DeepSeek key (S002-013).

## Verification Baseline (run between groups)

- `python -m pytest -q` (was 218 passed + 1 skipped pre-Wave-1)
- `cd web && npm run build` + `cd web && npm test` (was build green, vitest 32)
- Layer grep gates (control-manifest §6): no sys.path.insert under src/doge/,
  no sqlite3.connect/connect_duckdb in src/api routers, _PROJECT_ROOT only in settings.py.

## Workflow-Agent Lessons (from prior plan, still binding)

- **typescript-specialist FAILS StructuredOutput in schema workflows** (failed twice
  before). Use general-purpose (default) agents for any web/registry/ADR authoring
  that needs schema output. python-specialist + default agents are reliable.
- Registry writes (entities.yaml/architecture.yaml) are BLOCKING on user approval —
  but the baseline registries were approved last session; per-field edits within an
  approved file for an in-flight story are part of that story's changeset (not a new
  registry-wide approval). Surface any NEW registry entity for approval.
- ADR lifecycle: Proposed→Accepted never skipped; only S002-011 edits ADR Status lines.

## After Wave 1

- Wave 2: ops docs (GETTING_STARTED/API/CLI/operations-runbook + design/ux seeds + README refresh)
- Wave 3: MODULARIZATION batches 1/4/5/6 (recon verified: src/doge/ scaffolding complete
  but DORMANT; live path still legacy mcp_server.py + src/cli.py + src/api routers w/ direct DB;
  macro↔micro "cycle" is actually one-way micro→macro — plan diagram was wrong)
- Wave 4: /gate-check + /architecture-review in FRESH sessions; adoption audit 0/0/0

## Open Items / Flags

- S002-010 full error.code-branching deferred until S002-009's string-enum lands.
- S002-004 INJECT-PORT default-adapter construction must move to a composition root
  or AC-2 (services import no infrastructure) still fails.
- S002-013 operator must revoke key + export DEEPSEEK_API_KEY before GUI/macro runs work.
<!-- STATUS -->
Epic: Verification / Release-Ready v1
Feature: Sprint 003 — Verification
Task: S003-003 + S003-011 done; S003-002 user-test still needs operator action; next code story S003-012 perf profile or S003-013 CORS deferral record
<!-- /STATUS -->
