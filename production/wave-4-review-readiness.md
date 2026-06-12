# Wave 4 — Review-Readiness Checklist (Release-Ready v1 收尾)

> **Status:** Wave 4 cleanup applied 2026-06-12 · **Owner:** fresh-session reviewer (implementer cannot self-review per CLAUDE.md)
> **Branch:** `cdd-adoption-2026-06-11` · **Stage:** `Implementation` (production/stage.txt)
> **Purpose:** Advance the project from Implementation to release-ready. Wave 4 = two fresh-session gates + adoption audit to zero. This file is the item-by-item checklist to run before opening a fresh session, and the script to run inside it.

---

## §0 Hard Constraints

- `/gate-check` and `/architecture-review` **MUST run in fresh Claude sessions** — the implementer session is biased and cannot self-review.
- ADR lifecycle: Proposed→Accepted never skipped; ADR-0009/0010 were promoted by the Wave 4 architecture-review follow-up.
- Registry writes (entities.yaml / architecture.yaml) remain BLOCKING on per-item user approval; baseline already approved this sprint, new entries need re-confirmation.
- Commits carry NO co-author trailer (standing user constraint).

---

## §1 Pre-flight Checklist (verify GREEN before opening a fresh session)

| # | Check | Command / evidence | Expected |
|---|---|---|---|
| P1 | Full pytest | `python -m pytest -q` | **499 passed / 2 skipped / 6 xfailed / 0 failed** |
| P2 | Web build | `cd web && npm run build` | green (vendored @pretext) |
| P3 | Web tests | `cd web && npm test` | 49 passed |
| P4 | `src/` + `doge_mcp.py` sys.path gate | `grep -rnE "sys.path.insert\|sys.path.append" src/ doge_mcp.py` | only allowed test/bootstrap references; 0 clean-tree/runtime hits |
| P5 | No monolith in MCP entrypoints | `grep -rn "mcp_server.py" scripts/ .mcp.json` | 0 (retargeted to doge_mcp.py) |
| P6 | Interface sqlite3 gate (known PARTIAL) | `grep -rlE "import sqlite3\|sqlite3.connect" src/api/` | scan.py clean; data/macro/analysis/main still red (router-DI deferred — documented) |
| P7 | Clean working tree | `git status --short` (excl. session-state/logs) | only session artifacts |
| P8 | Editable install active | `python -c "import doge,micro,macro,ai_analysis,api,interface"` | imports without sys.path tricks |
| P9 | ADR status self-consistent | `pytest tests/unit/governance -q` | lifecycle guard passes |

> If P1–P9 all green → open a fresh session. Any red → fix in the implementer session first; do not carry a broken state into review.

---

## §2 `/gate-check` Readiness (fresh session ①)

Checks whether the project can advance stage (Implementation → release). Have ready:

- **`production/stage.txt`** = `Implementation` (confirmed).
- **`production/sprint-status.yaml`**: S001 done, S002 done (13/13), rollup done:13 (confirmed).
- **Test evidence**: P1–P3 green output.
- **Gate evidence**: P4–P6 grep results (declare P6's partial-red honestly — router DI deferred, API still works).
- **CDD coverage**: `design/cdd/module-index.md` — all 12 modules Designed.
- **Ops docs**: docs/GETTING_STARTED, API, CLI, operations-runbook present.

**Expected outcome**: gate passes; the router-DI / TDX-stub / RSRS-view-inversion items may appear as pre-release recommendations — record them, they do not block.

---

## §3 `/architecture-review` Readiness (fresh session ② — the main event)

The fresh review decides 4 categories. **Prepare evidence for each.**

### 3.1 ADR Promotion (core action) — completed
| ADR | Current | Recommended verdict | Evidence |
|---|---|---|---|
| 0009 cache/metadata port split | **Accepted** | **Accepted by Wave 4** | ITickerNameCache + ITickerMetadataSource declared; YFinanceMetadataSource stub (mirrors TDX pattern); decision realized, real .info adapter is a follow-on impl item, not a gate |
| 0010 view-service port injection | **Accepted** | **Accepted by Wave 4** | IMarketViewRepository + DuckDBMarketViewRepository + 4 services converted + composition root; AC-2 grep clean (only composition.py imports infra) |
| 0004 data-source adapter | Proposed | **keep Proposed** | TDX still a NotImplementedError stub → gate unmet |
| 0007 API surface/CORS | Proposed | **keep Proposed** | error envelope (S002-009) met; CORS hardening (allow_origins=['*']) out of Sprint scope |

Wave 4 follow-up flipped the ADR Status lines, updated governance tests, and
kept ADR-0004/0007 gated.

### 3.2 Batch-6 (`mcp_server.py` deletion) — completed
- **[B1 ✅ DONE]** `tests/test_mcp_notes_softdelete.py` retargeted onto the modular `stock_overview` (the live path; was guarding the dead legacy monolith). 3 original scenarios + assertions preserved; patches via `DOGE_RESEARCH_DB` + `reset_settings()` + a fake `build_stock_service`.
- **[B2 ✅ DONE]** `tests/integration/mcp/test_modular_legacy_parity.py` — parametrized 6-tool byte-for-byte parity (`@pytest.mark.integration`, auto-skips without the live DB, CI-excludable). **Result: all 6 tools hold EXACT parity — zero modular divergences, no live-server code changes needed.** Strong evidence the modular server is a true drop-in.
- **Wave 4 action complete:** `mcp_server.py` deleted, `doge_mcp.py` sys.path compat shim removed, and the layer-gate tolerated-entrypoint carve-out dropped (`tests/unit/layer_gates/test_no_sys_path_shims_under_src.py`).
- **One nuance for the reviewer (non-blocking):** modular `stock_overview` uses a single try/except for names+notes vs legacy's two-block form — invisible on any populated DB, behavior-neutral. Decide converge-vs-leave; does not block deletion.

### 3.3 Three "known issue" decisions (reviewer must rule)
| Issue | Current state | Decision needed |
|---|---|---|
| **DuckDB vw_rsrs_ranking sign inversion** | **RESOLVED (S003-005, 2026-06-12)** — view now regresses on ASC time index (`rn_asc`); live view re-materialized; view+Python parity verified to 1e-5 on real tickers; DDL moved under VCS at `src/doge/infrastructure/database/views.sql`; strict `xfail` removed (now a hard regression guard) | n/a — done |
| API router DI (§6 partial red) | data/macro/analysis/main still direct sqlite3.connect | Do deps.py + 6-router service-injection now, or defer to Wave 5? |
| TDX adapter | tdx.py stub | Migrate now, or defer (blocks tdx_downloader full retirement + ADR-0004 promotion)? |

### 3.4 Adoption audit re-run
- Target: **0 blocking / 0 high / 0 medium** (previous round already zeroed; new items this sprint need re-check).
- Focus: new ADR-0009/0010, modular MCP, vendored @pretext, StorageWriteError adoption consistency.

---

## §4 Deferred-Items Disposition Table

| Item | Category | Disposition | Evidence / location |
|---|---|---|---|
| Batch-6 monolith deletion | gate prerequisite | **DONE** — parity evidence retained; monolith deleted | §3.2 |
| ADR-0009/0010 promotion | governance | **DONE** — both Accepted | §3.1 |
| API router DI | architecture | Reviewer rules (recommend Wave 5) | §3.3 |
| TDX adapter migration | architecture | Reviewer rules (recommend Wave 5) | §3.3 |
| RSRS view sign inversion | correctness | **Fix in Wave 4** (incl. DDL versioning) | §3.3 |
| Test-bootstrap sys.path (12 sites) | cleanup | Wave 5 (out of control-manifest scope) | recon record |
| MCP tool error-text sanitization | security/hygiene | Wave 5 (suggestion) | code-review W-01 |
| `wmic` → CIM | portability | Wave 5 (before Win11/Server 2025) | code-review W-02 |
| **DeepSeek key rotation** | security | **Operator — do now** | revoke+reissue at console; env path ready |

---

## §5 Operator Steps (cannot be automated)

1. In the DeepSeek console, **revoke** the historically-on-disk key (sk-72a6f08d…) and **reissue**.
2. `set DEEPSEEK_API_KEY=<new-key>` (or PowerShell / bash equivalent).
3. Verify: `python -m macro.cli` (or the GUI) produces a macro report.
4. Note: the key was NEVER in git history (gitignored + untracked — confirmed); no history scrub needed.

---

## §6 Fresh-Session Execution Script (copy-paste)

**Session ① — gate-check**
```
1. /project-stage-detect   (confirm stage)
2. /gate-check             (run gates; present P1–P9 evidence)
```

**Session ② — architecture-review**
```
1. /architecture-review    (review ADRs; promote 0009/0010 per §3.1)
2. §3.2 — confirm Batch-6 completion: mcp_server.py deleted, doge_mcp.py shim removed, layer-gate carve-out dropped
3. Rule on §3.3 → decide RSRS view fix + router-DI/TDX Wave-5 ownership
4. Re-run adoption audit → expect 0/0/0
5. /story-done  to close S002-011
```

---

## §7 Reference Artifacts

- Plan source: `C:\Users\WSMAN\.claude\plans\mellow-greeting-pinwheel.md`
- Code review: `production/code-reviews/code-review-mcp-modular-server-2026-06-12.md`
- Sprint: `production/sprints/sprint-002-cdd-followup.md` · status: `production/sprint-status.yaml`
- ADRs: `docs/architecture/adr-000{1..8}-*.md`, `adr-0009-cache-metadata-port-split.md`, `adr-0010-view-service-port-injection.md`
- Control manifest: `docs/architecture/control-manifest.md` (Manifest Version 2026-06-12)
- Recon specs (implementer reference): `C:\Users\WSMAN\AppData\Local\Temp\claude\...\tasks\whc0wdaq9.output`
