# Active Session State

> Living checkpoint. Gitignored. Read this first after any compaction/crash.
> Branch: `cdd-adoption-2026-06-11` · Date: 2026-06-13

## Current Task

**Sprint 004 (Release clean-PASS prep) — implementation COMPLETE; awaiting fresh-session gates.**
Operator chose Phase-4 path (A) clean PASS. Sprint 004 code work is committed
(7 stories, `b44d6a7`→`c78498b`); 568 pytest passed / 2 skipped / 0 failed;
§6 layer gate GREEN; verification-milestone all exit criteria [x].

Sprint 004 stories (all committed):
- S004-001/002 INoteRepository port + adapter; notes.py off ai_analysis (`d6dcb5d`)
- S004-003 query_stock → get_ticker_with_context, §6 GREEN (`8bc4c5e`)
- S004-004 TDX adapter real impl; ADR-0004 gate met (`b989ef9`)
- S004-005 ADR-0007 strengthened-loopback-guarantee (`9696ec3`)
- S004-006 verification-milestone all exit criteria [x] (`fe45585`)
- S004-007 doc fixes — yfinance rate-limit + CLI exit-code table (`d8b1886`)
- S004-008a ADR-0004 → Accepted + TR-045/046 + TR-011 (`c78498b`)

**NEXT (fresh-session operator actions — this session implemented the work, cannot self-certify):**
1. Fresh `/architecture-review` — brief: `production/architecture-reviews/architecture-review-brief-s004.md`.
   Authorizes ADR-0007 loopback promotion (its authority per ADR-0007:46-49),
   verifies ADR-0004, rules on the TDX `connect(self, market)` signature.
2. S004-008b: flip ADR-0007 → Accepted + governance test (after the arch-review
   signs off).
3. Fresh `/gate-check` (Verification → Release) — aim clean PASS.

State: ADR-0001/2/3/4/5/8/9/10 Accepted; ADR-0007 Proposed (arch-review-gated).

## Latest Verification Run (2026-06-13)

- `python -m pytest -q` → **514 passed, 2 skipped, 0 failed** (+6 new key-redaction regression tests; PyQt6 DLL-load fatal exception remains ADVISORY-only).
- `pytest tests/unit/macro/test_strategist_no_key_in_logs.py -v` → **4 passed** (repr + data_loader redaction).
- `pytest tests/cli/test_macro_cli_error_redaction.py -v` → **3 passed** (CLI error-path redaction).
- `pytest tests/cli/test_runbook_retention_examples.py -q` → **13 passed, 1 skipped, 0 failed**.
- `cd web && npm test` → **70 passed**.
- `cd web && npm run build` → **green**.

SSE transport test (`tests/test_transport.py::TestSseTransport::test_sse_endpoint_exists`) was failing due to a stale `.mcp_server.pid` file with 99 entries causing synchronous `wmic` subprocess calls to block the async SSE lifespan. Fixed in commit `02369b2`.

## Blockers Cleared

- ✅ SSE transport test stable.
- ✅ S003-010 DeepSeek key environment verification PASS.
- ✅ S003-002 unguided walkthrough PASS after opentdx import-guard fix.

## Next Step

**Sprint 003 已正式关闭为 13/13 done。**

- Final close commit: `57a217a chore(sprint): S003 all 13/13 done`
- Scanner fix + evidence commit: `5fd26ee fix(scanner): guard opentdx import ...`
- Verification suite: 519 pytest passed / 2 skipped; web build/test green.

后台进程和临时 CDP 脚本已清理。

未提交工作树：
- `production/session-logs/session-log.md`（历史审计日志，不提交）
- `production/session-logs/compaction-log.txt`（未跟踪）
- `production/session-state/active.md`（会话状态，本次编辑）

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
| S002-013 key→env migration | placeholder + env-primary + hard RuntimeError; drop api_key from /config; GUI requires env export |

**Operator-only step:** verify `DEEPSEEK_API_KEY` is exported and `python -m macro.cli`
runs. Forensic audit of 82 commits / 4 refs / reflog / all dangling objects confirmed
no real DeepSeek key was ever committed to git history (`models_config.json` was
gitignored from the initial commit). Revocation is unnecessary; only environment
availability verification remains.

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
- Operator step: verify `DEEPSEEK_API_KEY` is exported and `python -m macro.cli` works
  (S002-013). Forensic audit confirmed no real key was ever committed to git history.

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
- S002-013 operator must export `DEEPSEEK_API_KEY` and verify `python -m macro.cli` runs
  before GUI/macro workflows work. No key rotation needed: forensic audit found no
  real key in git history.
<!-- STATUS -->
Epic: Verification / Release-Ready v1
Feature: Sprint 004 — Release clean-PASS prep
Task: impl complete (7 stories); fresh /architecture-review + /gate-check next
<!-- /STATUS -->

## Session Extract — /architecture-review 2026-06-13

- Verdict: CONCERNS
- Scope: focused S003-014 review of ADR-0004 / ADR-0007 promotion or deferral eligibility
- Requirements: no full CDD-wide TR rebuild performed; focused sprint-governance review only
- New TR-IDs registered: None
- CDD revision flags: None
- Top ADR gaps: ADR-0004 TDX adapter still raises NotImplementedError; ADR-0007 CORS hardening remains deferred
- Report: production/architecture-reviews/architecture-review-s003-014-2026-06-13.md
