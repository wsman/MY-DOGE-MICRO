# Sprint 002 -- CDD Follow-up & Technical Debt

## Sprint Goal

Retire the technical debt surfaced by the comprehensive architecture review and
the open questions recorded across the twelve module CDDs: unify the divergent
RSRS implementations, close the two unresolved port-naming decisions, eliminate
the named forbidden-pattern offenders, fix the silent retention-truncation and
config-drift bugs, harden the API error envelope and SSE reconnect path,
promote the two overstretched Proposed ADRs whose decisions already ship, make
the `@pretext` alias portable, and rotate the locally-stored DeepSeek API key
into an env var.

## Milestone Context

- **Current Milestone**: Implementation / Brownfield Modularization
- **Milestone Deadline**: Not set
- **Sprints Remaining**: Not set
- **Predecessor**: Sprint 001 (Brownfield Metadata Import) — Complete (web build evidence S001-012 Blocked)
- **Control Manifest**: 2026-06-12

## Capacity

> **Duration assumption**: 2 weeks. Days below are notional effort estimates
> (S/M/L) per story, not wall-clock assignments; capacity rows mirror Sprint
> 001's format.

| Resource | Available Days | Allocated | Buffer (20%) | Remaining |
|----------|----------------|-----------|--------------|-----------|
| Programming | Not set | Not set | Not set | Not set |
| Design | Not set | Not set | Not set | Not set |
| QA | Not set | Not set | Not set | Not set |
| **Total** | Not set | Not set | Not set | Not set |

## Scope

This sprint consumes the **remaining** architecture-review backlog. The
original Sprint 001 bug backlog (Bug A `delete_note` soft-delete, Bug B yfinance
adapter, Bug C module-#6 rename, Bug E test coverage) is **RESOLVED** and is
not re-covered here.

Out of scope for Sprint 002 (deferred to later sprints):
- Authoring the missing Module #6 CDD (FINDING-2).
- Populating `docs/registry/entities.yaml` (FINDING-5).
- The full TDX adapter migration beyond removing the `sys.path.insert` shim
  (TR-011 full NotImplementedError removal).
- CORS hardening for ADR-0007 (only the error-envelope half is in scope).

## Story Backlog

### Story Table

| Story ID | Title | Epic | TR-ID | Priority | Effort | Owner Role | Status |
|----------|-------|------|-------|----------|--------|------------|--------|
| S002-001 | RSRS sign-convention unification (Python scalar / vectorized / DuckDB-SQL) | ep-architecture-debt | TR-016 (OQ-11) | MED | M | python-specialist | Todo |
| S002-002 | Macro local RSRS copy: add flat-variance + NaN guards | ep-architecture-debt | TR-016 | MED | S | python-specialist | Todo |
| S002-003 | Decide cache-port vs metadata-port split (TickerMetadataSource vs Cache/ITickerNameCache) | ep-architecture-debt | TR-042 (OQ-2) | MED | M | lead-programmer | Todo |
| S002-004 | Decide view-service port injection (IMarketViewRepository OR amend ADR-0001) | ep-architecture-debt | TR-041 (OQ-5) | MED | M | lead-programmer | Todo |
| S002-005 | Forbidden-pattern remediations (scan.py init_db_custom import, MomentumRanker.get_connection sqlite3.connect, tdx_downloader.py sys.path.insert) | ep-architecture-debt | TR-011, TR-040 | MED | S | python-specialist | Todo |
| S002-006 | Replace swallowed write exception with logged StorageWriteError | ep-architecture-debt | TR-006 | MED | S | python-specialist | Todo |
| S002-007 | **Resolve retention_days vs analytical-view window mismatch (silent-truncation fix)** | ep-storage-consistency | TR-006 | **HIGH** | M | python-specialist | Todo |
| S002-008 | Reconcile models_config.json scanner_filters vs Settings().market.* (single source of truth) | ep-storage-consistency | TR-019 | MED | M | python-specialist | Todo |
| S002-009 | Stable non-leaking API error envelope via global exception handler | ep-api-resilience | TR-030 | MED | M | python-specialist | Todo |
| S002-010 | SSE reconnect / watchdog: dropped stream surfaces terminal error, not stuck "running" | ep-api-resilience | TR-036 | MED | M | typescript-specialist | Todo |
| S002-011 | Promote ADR-0002 + ADR-0005 to Accepted; define promotion gates for ADR-0003/0004/0007 | ep-governance-security | (FINDING-1) | MED | S | lead-programmer | Todo |
| S002-012 | Make @pretext sibling-project alias portable (vendor / npm-publish / workspace-alias) | ep-governance-security | TR-037 | MED | M | typescript-specialist | Todo |
| S002-013 | **Rotate DeepSeek API key to DEEPSEEK_API_KEY env var; placeholder in models_config.json** | ep-governance-security | TR-015 | **HIGH** | S | security-engineer | Todo |

### Priority Bands (MoSCoW)

#### Must Have (Critical Path)

| ID | Task | Owner | Est. Effort | Dependencies | Acceptance Criteria (summary) | Status |
|----|------|-------|-------------|--------------|-------------------------------|--------|
| S002-007 | Resolve retention_days vs view-window mismatch (silent-truncation fix) | python-specialist | M | None (pairs with S002-006 for TR-006) | `DOGE_RETENTION_DAYS` knob exists; default >= 730 OR view window <= retention; breadth scan returns window-promised rows past the old 180d boundary (BLOCKING migration test) | Todo |
| S002-013 | Rotate DeepSeek API key to env var; placeholder in models_config.json | security-engineer | S | None | Key read from `DEEPSEEK_API_KEY`; `models_config.json` ships placeholder; key never logged/printed; old on-disk key rotated (revoked + reissued) | Todo |

> **Rationale for Must Have**: S002-007 is the only **HIGH**-severity latent
> *correctness* bug (silent data truncation affecting breadth scans). S002-013
> is the only **security** item — a real API key sat on disk through the
> brownfield period; even though it never leaked (gitignored), the move + key
> rotation is hygiene that should not slip a sprint.

#### Should Have

| ID | Task | Owner | Est. Effort | Dependencies | Acceptance Criteria (summary) | Status |
|----|------|-------|-------------|--------------|-------------------------------|--------|
| S002-001 | RSRS sign-convention unification | python-specialist | M | None (feeds S002-002) | All three RSRS implementations agree on sign for zero/flat slope on identical input (parity test) | Todo |
| S002-002 | Macro local RSRS guards | python-specialist | S | S002-001 | Macro copy returns 0.0 not nan on flat/zero-variance + short series | Todo |
| S002-003 | Cache-port vs metadata-port split decision | lead-programmer | M | None | Accepted ADR or ADR-0001 amendment records the decision; TR-042 references it | Todo |
| S002-004 | View-service port-injection decision | lead-programmer | M | None | Accepted ADR or ADR-0001 amendment records the decision; TR-041 references it | Todo |
| S002-005 | Forbidden-pattern remediations (3 sites) | python-specialist | S | None | Grep gate clean for the three named sites; Batch-1 migration gate unblocked | Todo |
| S002-006 | Surface StorageWriteError | python-specialist | S | None (pairs with S002-007) | `save_stock_data_custom` logs/raises typed error; no bare `except: pass` | Todo |
| S002-008 | Config drift reconciliation | python-specialist | M | None | One canonical scanner-filter source; divergence test guards the mirror | Todo |
| S002-009 | API error envelope | python-specialist | M | None (feeds S002-010) | All errors conform to `{error:{code,message}}`; no raw `str(e)` or stack trace (BLOCKING contract test) | Todo |
| S002-010 | SSE reconnect / watchdog | typescript-specialist | M | S002-009 (soft) | Dropped stream drives terminal error state within bounded watchdog; `npm run build` + `npm test` green (BLOCKING) | Todo |
| S002-011 | ADR-0002/0005 promotion + gate definitions | lead-programmer | S | S002-006/007/009 (for the gate definitions) | ADR-0002 + ADR-0005 Accepted; ADR-0003/0004/0007 carry explicit promotion-gate notes | Todo |
| S002-012 | @pretext alias portability | typescript-specialist | M | None | `web/` builds on a clean checkout without the sibling pretext project | Todo |

#### Nice to Have (Cut First)

| ID | Task | Owner | Est. Effort | Dependencies | Acceptance Criteria (summary) | Status |
|----|------|-------|-------------|--------------|-------------------------------|--------|
| — | (No nice-to-have stories this sprint; all 13 are Should/Must. If capacity slips, cut S002-003 and S002-004 first — they are design/ADR decisions that can defer one sprint without code impact, while the code-touch stories carry BLOCKING evidence gates.) | — | — | — | — | — |

## Carryover from Sprint 001

| Original ID | Task | Reason for Carryover | New Estimate | Priority Change |
|-------------|------|----------------------|--------------|-----------------|
| S001-012 | Web build/type check evidence | Marked Blocked in Sprint 001 (clean-checkout build not yet green due to @pretext alias) | S | Now in scope as S002-012 (root-caused, not just re-evidence) |

> S001-012 was the one Blocked task in Sprint 001. Its root cause is the
> `@pretext` alias portability gap, which S002-012 fixes directly. S001-012 is
> therefore **not** carried forward as a separate task; it is subsumed by
> S002-012.

## Ordering & Rationale

Recommended execution order (top = start first):

1. **S002-013** (security) and **S002-007** (HIGH correctness) — start Day 1.
   No upstream dependencies; highest downside if deferred.
2. **S002-005** (forbidden-pattern shims) and **S002-006** (StorageWriteError) —
   quick wins that unblock Batch-1 migration and the ADR-0003 promotion gate.
3. **S002-001 → S002-002** (RSRS unification then macro guards) — sequence the
   canonical copy first so the macro delegation has a single source of truth.
4. **S002-009 → S002-010** (error envelope then SSE reconnect) — envelope first
   so the client can branch on `code`.
5. **S002-003, S002-004** (port-naming decisions) — design/ADR work; can run in
   parallel with the code stories and land any time in the sprint.
6. **S002-008** (config drift) — independent; slot where capacity allows.
7. **S002-012** (@pretext portability) — independent web-tree work.
8. **S002-011** (ADR promotions + gate definitions) — **last**, because its
   gate definitions for ADR-0003/0004/0007 reference the outcomes of S002-006,
   S002-007, and S002-009. The ADR-0002/0005 promotion half can happen earlier
   if desired.

## Risks to This Sprint

| Risk | Probability | Impact | Mitigation | Owner |
|------|-------------|--------|------------|-------|
| Raising `DOGE_RETENTION_DAYS` to 730 increases on-disk DB size beyond local-first memory/storage expectations | Medium | Medium | Measure DB size delta before/after; document the new steady-state size in `market-data-storage.md`; offer a documented "short retention + short view" paired fallback | python-specialist |
| RSRS sign-convention change alters historical scanner/CSV output, breaking downstream operator expectations | Medium | Medium | Pin the chosen convention in a parity test; document the before/after in `micro-momentum-scanner.md` §4.1 sign-convention note; communicate in patch notes | python-specialist |
| Port-naming decisions (S002-003/004) trigger ADR-0001 amendments that ripple into Batch-4 of the migration sequence | Medium | Medium | Treat both as Proposed ADRs first; do not edit ADR-0001 in place to reverse its decision — supersede or amend formally | lead-programmer |
| @pretext vendoring bloats the web bundle or breaks the lightweight-charts integration | Low | Medium | Verify `npm run build` bundle size before/after; run the full `npm test` smoke suite | typescript-specialist |
| API-key rotation disrupts a live operator session using the old key | Low | High | Coordinate rotation window; ship the env-var read + placeholder before revoking the old key; document the `DEEPSEEK_API_KEY` setup in `docs/MCP_SERVER.md` and `runtime-configuration.md` | security-engineer |
| Sprint capacity (2 weeks) is insufficient for 13 stories | High | Medium | Cut order is defined (S002-003/004 first); BLOCKING-gated code stories (S002-006/007/009/010) are protected | lead-programmer |

## External Dependencies

| Dependency | Status | Impact if Delayed | Contingency |
|------------|--------|-------------------|-------------|
| DeepSeek API console (for key rotation) | Available | S002-013 cannot fully close until the old key is revoked + reissued | Ship the env-var move + placeholder first; rotation can follow within days |
| Sibling `pretext` project (for S002-012 verification) | Local only | Cannot prove portability without a clean checkout test | Use a throwaway clean clone in CI or a fresh directory to verify the build |
| `docs/architecture/tr-registry.yaml` (read-only reference) | Stable (2026-06-12) | Story TR-IDs must exist and be `active` for `/story-readiness` | All 13 stories reference existing active TRs (TR-006, TR-011, TR-015, TR-016, TR-019, TR-030, TR-036, TR-037, TR-040, TR-041, TR-042) |

## Definition of Done

- [ ] All BLOCKING-gated stories (S002-006, S002-007, S002-009, S002-010) have
  passing contract/migration/interaction tests in the required locations.
- [ ] `python -m pytest -q` is green on Windows 10 LTSC.
- [ ] `npm run build` and `npm test` are green in `web/` on a clean checkout.
- [ ] Layer-rule grep gates (`control-manifest.md §6`) pass for the remediated
  sites.
- [ ] ADR-0002 and ADR-0005 read `Status: Accepted`; ADR-0003/0004/0007 carry
  explicit promotion-gate notes.
- [ ] No real API key remains in `models_config.json`; the on-disk key has been
  rotated.
- [ ] All 13 stories' acceptance criteria are met or explicitly deferred with a
  recorded reason.
- [ ] Commits reference the relevant Story ID (S002-NNN) and TR-ID.

## Daily Status Tracking

| Day | Tasks Completed | Tasks In Progress | Blockers | Notes |
|-----|-----------------|-------------------|----------|-------|
| Day 1 | — | — | — | Sprint planned; awaiting kickoff |

## Related Artifacts

- Epics: `production/epics/index.md` and `production/epics/<slug>/EPIC.md`
- Machine-readable status: `production/sprint-status.yaml`
- Findings: `docs/architecture/architecture-traceability.md` §6 (FINDINGS) and §7
- Requirement IDs: `docs/architecture/tr-registry.yaml`
- Control plane: `docs/architecture/control-manifest.md` (Manifest Version 2026-06-12)
