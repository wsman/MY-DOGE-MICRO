# Sprint 003 — Verification

> **Stage**: Verification  
> **Sprint Goal**: 完成 Verification 阶段出口证据，关闭 gate-check CONCERNS 中高影响项，为 Verification → Release 门控奠定基础。  
> **Duration**: 2 weeks  
> **Start**: 2026-06-12  
> **End**: 2026-06-26  
> **Predecessor**: Sprint 002 — CDD Follow-up & Technical Debt (13/13 done)  
> **Control Manifest**: 2026-06-12  

---

## Milestone Context

- **Current Milestone**: Verification / Release-Ready v1  
- **Milestone Deadline**: 2026-06-26 (see `production/milestones/verification-milestone.md`)  
- **Predecessor**: Sprint 002 complete; `production/stage.txt` advanced Implementation → Verification under CONCERNS verdict with recorded risk note (`production/gate-checks/gate-implementation-verification-2026-06-12.md`).  

## Scope

### In Scope

Sprint 003 consumes the **high-impact Verification backlog** surfaced by `/gate-check`:

- User-test / workflow validation evidence for the core operator path.
- QA plan and smoke-check artifacts required before Verification → Release.
- Performance baseline profile against declared budgets.
- API router dependency injection (close direct DB connections in `src/api/routers/`).
- RSRS view sign-inversion fix with DDL under version control.
- CORS / ADR-0007 formal deferral record.
- FRESH `/architecture-review` for ADR-0004/0007 end-state sign-off.

### Explicitly Out of Scope

These Wave-5 hygiene items are **deferred** and must not be pulled into Sprint 003:

- 12 test-bootstrap `sys.path` cleanup sites.
- MCP tool error-text sanitization.
- `wmic` → CIM portability migration.

### TDX Adapter Decision

`S003-004` TDX adapter real implementation is **deferred** from Sprint 003. `tdx_downloader.py` continues to work as the live path; ADR-0004 remains Proposed until the adapter lands. This is recorded in §Deferred Items below.

---

## Story Backlog

### Must Have

| Story ID | Title | Epic | TR-ID | Priority | Effort | Owner Role | Status |
|----------|-------|------|-------|----------|--------|------------|--------|
| S003-001 | 里程碑截止日定义 + Sprint 003 基线 | ep-verification-evidence | — | HIGH | S | producer | Todo |
| S003-002 | 核心工作流用户验证报告（scanner → report → archive） | ep-verification-evidence | — | HIGH | M | ux-designer / qa-lead | Todo |
| S003-003 | API 路由依赖注入（deps.py + 路由脱离 sqlite3.connect） | ep-architecture-cleanup | TR-041 | HIGH | L | python-specialist | Todo |
| S003-005 | RSRS 视图符号修复 + DDL 版本化 | ep-architecture-cleanup | TR-016 | HIGH | M | python-specialist | Todo |
| S003-011 | QA / smoke 计划（Verification → Release 硬性交付物） | ep-verification-evidence | — | HIGH | M | qa-lead | Todo |
| S003-012 | 性能基线 profile | ep-verification-evidence | — | HIGH | M | performance-analyst | Todo |

### Should Have

| Story ID | Title | Epic | TR-ID | Priority | Effort | Owner Role | Status |
|----------|-------|------|-------|----------|--------|------------|--------|
| S003-006 | 缺失的 per-view UX flow specs（ticker/archive/analysis/insights） | ep-ux-polish | — | MED | M | ux-designer | Todo |
| S003-007 | Art bible / product style guide + design tokens | ep-ux-polish | — | MED | M | art-director / ui-programmer | Todo |
| S003-008 | 可访问性基线闭合 | ep-ux-polish | — | MED | M | accessibility-specialist | Todo |
| S003-009 | 5/6 视图的 loading/empty/error 三态补齐 | ep-ux-polish | TR-036 | MED | M | typescript-specialist | Todo |

### Nice to Have / Governance

| Story ID | Title | Epic | TR-ID | Priority | Effort | Owner Role | Status |
|----------|-------|------|-------|----------|--------|------------|--------|
| S003-010 | DeepSeek 密钥轮换操作 | ep-verification-evidence | TR-015 | MED | S | operator | Todo |
| S003-013 | CORS（ADR-0007）延期决策记录 | ep-governance | — | MED | S | lead-programmer | Todo |
| S003-014 | FRESH `/architecture-review`（ADR-0004/0007 终态签字） | ep-governance | — | MED | S | lead-programmer | Todo |

### Deferred Items (not in Sprint 003)

| ID | Title | Reason for Deferral | Target |
|----|-------|---------------------|--------|
| S003-004 | TDX 适配器真实实现 | User impact lowest among architecture cleanup; `tdx_downloader.py` still works; ADR-0004 promotion not a Verification → Release hard blocker | Future sprint post-Verification |

---

## Priority Bands

### Must Have (Critical Path)

| ID | Task | Owner | Est. Effort | Dependencies | Acceptance Criteria (summary) | Status |
|----|------|-------|-------------|--------------|-------------------------------|--------|
| S003-001 | 里程碑 + sprint 基线 | producer | S | None | `production/milestones/verification-milestone.md` exists with target date 2026-06-26 and exit criteria | Todo |
| S003-002 | 用户验证报告 | ux-designer / qa-lead | M | S003-001 (milestone context) | One `production/qa/evidence/user-tests/user-test-001-*.md` documenting an unguided end-to-end operator walkthrough (scanner → report → archive) | Todo |
| S003-003 | API 路由 DI | python-specialist | L | None | 0 direct `sqlite3.connect` / `connect_duckdb` in `src/api/routers/` and `src/api/main.py`; layer gate tests pass; services injected via `deps.py` | Todo |
| S003-005 | RSRS view sign fix | python-specialist | M | None | `vw_rsrs_ranking` sign convention matches Python RSRS path; DDL moved under version control; xfail removed | Todo |
| S003-011 | QA / smoke 计划 | qa-lead | M | S003-001 | `production/qa/qa-plan-verification.md` exists; at least one `production/qa/smoke/smoke-2026-06-*.md` covering 3 surfaces (CLI / API / Web or MCP) | Todo |
| S003-012 | 性能基线 profile | performance-analyst | M | S003-001 | `production/qa/evidence/perf/profile-*.md` exists; measurements against `standards/technical-preferences.md` budgets (MCP ≤30s, DB reads, UI off-thread) | Todo |

### Should Have

| ID | Task | Owner | Est. Effort | Dependencies | Acceptance Criteria (summary) | Status |
|----|------|-------|-------------|--------------|-------------------------------|--------|
| S003-006 | Per-view UX flow specs | ux-designer | M | S003-001 | `ticker-flow.md`, `archive-flow.md`, `analysis-flow.md`, `insights-flow.md` exist and reference `interaction-patterns.md` | Todo |
| S003-007 | Art bible / style guide | art-director / ui-programmer | M | S003-006 (flow context) | `design/art/art-bible.md` or `design/brand/style-guide.md` exists with dark-theme palette, type scale, spacing grid; inline view colors extracted to tokens | Todo |
| S003-008 | Accessibility baseline | accessibility-specialist | M | S003-006 | All OPEN items in `design/ux/accessibility-requirements.md` closed or formally deferred with rationale | Todo |
| S003-009 | Triad gaps closure | typescript-specialist | M | S003-006 | Loading/empty/error surfaces implemented for Ticker, CnArchive, UsArchive, Analysis, Insights; `interaction-patterns.md` §5 updated | Todo |

### Nice to Have / Governance

| ID | Task | Owner | Est. Effort | Dependencies | Acceptance Criteria (summary) | Status |
|----|------|-------|-------------|--------------|-------------------------------|--------|
| S003-010 | DeepSeek key rotation | operator | S | None | Old key revoked and reissued in console; `DEEPSEEK_API_KEY` exported; `python -m macro.cli` produces a macro report | Todo |
| S003-013 | CORS deferral record | lead-programmer | S | None | ADR-0007 or readiness doc records deferral rationale: local-first loopback-only, `allow_origins=['*']` currently acceptable | Todo |
| S003-014 | FRESH `/architecture-review` | lead-programmer | S | S003-003, S003-005, S003-013 | Fresh session runs `/architecture-review`; ADR-0004/0007 states finalized with documented rationale | Todo |

---

## Ordering & Rationale

1. **Day 1**: Start **S003-002** (user test scheduling/execution) and **S003-001** (milestone baseline). User validation is the longest-lead real-world activity.
2. **Week 1**: Run **S003-003** (API DI), **S003-005** (RSRS fix), and **S003-011** (QA plan) in parallel. Record **S003-013** (CORS deferral).
3. **Week 2**: Run **S003-012** (perf profile), **S003-006~009** (UX polish, capacity permitting), **S003-014** (fresh `/architecture-review`), and **S003-010** (operator key rotation).

**Cut order if capacity is insufficient**: S003-007 → S003-009 → S003-008 → S003-006.

---

## Risks to This Sprint

| Risk | Probability | Impact | Mitigation | Owner |
|------|-------------|--------|------------|-------|
| User-test scheduling slips | Medium | High | Start S003-002 on Day 1; use operator self-walkthrough with screen recording as fallback | ux-designer / qa-lead |
| API DI touches many legacy routers and breaks tests | Medium | Medium | Incremental router-by-router migration; keep existing tests green; add contract tests | python-specialist |
| RSRS view fix requires re-materializing large DuckDB views | Low | Medium | Test on representative dataset; document DDL versioning strategy | python-specialist |
| 2-week capacity insufficient for 6 Must-Haves + Should-Haves | Medium | Medium | Cut order defined; TDX deferred; UX polish scoped to specs first, code second | producer |

---

## Definition of Done

- [ ] At least one user-test report exists in `production/qa/evidence/user-tests/`.
- [ ] Milestone document exists at `production/milestones/verification-milestone.md` with deadline 2026-06-26.
- [ ] QA / smoke plan exists and covers at least 3 surfaces.
- [ ] Performance baseline profile exists and is compared against declared budgets.
- [ ] `src/api/routers/` and `src/api/main.py` contain no direct `sqlite3.connect` / `connect_duckdb` calls.
- [ ] RSRS view sign inversion is fixed and DDL is under version control.
- [ ] ADR-0004 and ADR-0007 states are finalized with documented rationale (promoted or deferred).
- [ ] `python -m pytest -q` green; `cd web && npm run build` green; `cd web && npm test` green.
- [ ] Layer-rule grep gates pass.

---

## Related Artifacts

- Gate check report: `production/gate-checks/gate-implementation-verification-2026-06-12.md`
- Wave 4 readiness doc: `production/wave-4-review-readiness.md`
- Milestone: `production/milestones/verification-milestone.md`
- Sprint status (machine-readable): `production/sprint-status.yaml` (to be updated when this sprint is ratified)
- Epics: `production/epics/index.md`
