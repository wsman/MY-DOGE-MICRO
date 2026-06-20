# Release Report: MY-DOGE-MICRO v0.2.1

**Release Date:** 2026-06-14  
**Version:** v0.2.1  
**Tag:** `v0.2.1` (annotated tag object `e14525d` points to commit `7217821738b9d4032c8e1ba5839c7b3198638b71`)  
**Branch:** `cdd-adoption-2026-06-11`  
**Previous Release:** v0.2.0 (`ad45634`)  
**Post-Tag Governance Evidence Commits:** `ba883a3` (launch checklist), `3b0bc2e` (release report), `785b4e8` (active state); tag NOT moved  
**Stage:** Release  
**Deployment Model:** Local-first, single-operator, loopback-only

---

## 1. Release Scope

`v0.2.1` is a patch release folding the post-`v0.2.0` architecture-hygiene tail into the Release baseline and aligning package metadata with the git tag.

### Shipped Changes (since v0.2.0)

- **S006-006** — `src/ai_analysis/fetch_names.py` migrated onto the `ITickerMetadataSource` port via `build_metadata_source()`.
- **Package version alignment** — `pyproject.toml` version bumped from `0.1.0` to `0.2.1`.
- **Release documentation** — `CHANGELOG.md` v0.2.1 section, release checklist, and launch checklist added.

### Explicitly Out of Scope / Deferred

- ADR-0007 path 1a (auth + non-loopback CORS allow-list) — conditionally deferred.
- CI/CD pipeline, formal a11y audit, Core Web Vitals, soak testing.
- Monitoring, alerting, crash reporting, on-call rotation — not applicable to single-operator local product.
- Rollback / hotfix pipeline documentation — future ops improvement.

---

## 2. Go / No-Go Decision

**Verdict: GO — CONDITIONAL**

### Sign-Off Status

| Role | Sign-Off | Basis |
|---|---|---|
| **Producer / Product Owner** | ✅ GO | Milestone acceptance criteria met; CONDITIONAL posture documented and accepted |
| **QA Lead** | ✅ Approved | 617 pytest / 5 skipped / 0 failed; 70 vitest; demo exits 0; smoke + user tests evidenced |
| **Release Manager** | ✅ Verified | Tag, version, CHANGELOG, and both checklists aligned |
| **Security Engineer** | ✅ Approved | Secrets audit clean; ADR-0007 loopback guarantee enforced; no new risks from S006-006 |
| **Technical Director** | ✅ Inferred | All ADRs Accepted; §6 layer gates green; architecture review history clean |
| **Operator / Release Owner (WSMAN)** | ✅ Confirmed | Accepts local-first no-monitoring posture and CONDITIONAL release stance |

### Blocking Items

**None.**

### Conditional Items Accepted

1. No CI/CD pipeline — local verification only.
2. Legacy CLI modules contain intentional console output; API/MCP service paths are clean.
3. No formal a11y / Core Web Vitals / soak test.
4. No monitoring, alerting, crash reporting, or on-call.
5. No rollback / hotfix pipeline documented.
6. `industry_analyzer.py` proxy default `127.0.0.1:7890` — operator-local default.
7. ADR-0007 path 1a deferred — non-loopback deployment requires auth + CORS allow-list first.

---

## 3. Quality Evidence

| Gate | Result |
|---|---|
| `python -m pytest -q` | **617 passed, 5 skipped, 0 failed** |
| `cd web && npm test` | **70 passed** |
| `cd web && npm run build` | **green** |
| `python src/cli.py demo --market cn --top 3` | **exits 0 without `DEEPSEEK_API_KEY`** |
| §6 layer gate | **ZERO hits** |
| S006-006 regression test | `tests/unit/ai_analysis/test_fetch_names_metadata_port.py` — **4 passed** |

### Artifacts Referenced

- `production/releases/release-checklist-v0.2.1-2026-06-14.md`
- `production/releases/launch-checklist-v0.2.1-2026-06-14.md`
- `CHANGELOG.md`
- `production/qa/smoke/smoke-2026-06-12.md`
- `production/qa/evidence/user-tests/user-test-001-2026-06-13.md`
- `production/qa/evidence/user-tests/user-test-002-2026-06-13.md`
- `production/qa/evidence/user-tests/user-test-003-2026-06-13.md`

---

## 4. Deployment Status

| Item | Status |
|---|---|
| Git tag created and annotated | ✅ `v0.2.1` → `7217821` |
| Tag pushed to remote | ✅ |
| Release branch pushed to remote | ✅ `cdd-adoption-2026-06-11` |
| Package version aligned | ✅ `pyproject.toml` = `0.2.1` |
| Release notes published | ✅ `CHANGELOG.md` |
| Cloud deployment | **N/A** — local-first product |
| Store submission | **N/A** — not distributed through store |

---

## 5. 48-Hour Operator Observation Plan

Since this is a single-operator local product with no telemetry or monitoring, the operator is the first-line observer for the 48 hours following release.

### Hour 0–24

- [ ] Pull / verify the tag: `git fetch origin && git show v0.2.1`
- [ ] Re-install editable package: `pip install -e .`
- [ ] Run full local verification suite:
  - `python -m pytest -q`
  - `cd web && npm test && npm run build`
  - `python src/cli.py demo --market cn --top 3`
- [ ] Smoke the three runtime surfaces:
  - CLI: `python src/cli.py rsrs --top 10`
  - API: `python -m uvicorn doge.interfaces.api.main:app --host 127.0.0.1 --port 8901` then check `http://127.0.0.1:8901/api/health`
  - MCP: `python doge_mcp.py --transport stdio --log-level INFO`
- [ ] Confirm no unexpected `print()` debug output in normal operator workflows.

### Hour 24–48

- [ ] Run one end-to-end workflow (scanner → insights → archive → ticker) via web UI.
- [ ] Verify no new issues introduced by S006-006 in any workflow that touches ticker metadata.
- [ ] If any regression is observed, capture it in `production/session-logs/` and evaluate `/hotfix` or Sprint 007.

### Stop Conditions

- If any S1/S2 issue appears, pause further use of `v0.2.1` and open a hotfix.
- If the only issues are the already-documented conditional gaps (e.g., no monitoring), no action is required.

---

## 6. Memory Bank Note

`memory_bank/` does not exist in this workspace. Per `/team-release` skill rules, release evidence is **not** written to a memory bank here. To establish the memory-bank governance control plane, run `/constitute` in a future session.

---

## 7. Next Steps

1. Operator completes the 48-hour observation plan.
2. If no issues surface, stage may be considered stable at `Release`.
3. If issues surface, use `/hotfix` or open Sprint 007 / a new epic.
4. For future releases, run `/retrospective` to capture lessons learned.

**Release Status:** ✅ **DEPLOYED / LIVE** (local-first release; tag published)
