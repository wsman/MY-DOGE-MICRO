# Architecture Review: S003-014 ADR-0004 / ADR-0007 Finalization

> Review ID: S003-014  
> Date: 2026-06-13  
> Stage: Verification  
> Mode: focused `/architecture-review`  
> Scope: ADR-0004 and ADR-0007 promotion/defer decision for Sprint 003 closure

---

## Verdict: CONCERNS

Sprint 003 may close with ADR-0004 and ADR-0007 remaining **Proposed**, provided
the conditions below remain true and are tracked as post-Verification work.

This is not a clean PASS because both ADRs still have unfinished validation
criteria. It is not a FAIL because neither unfinished item blocks the current
local-first Verification scope:

- ADR-0004: the TDX adapter is still a stub, but the live compatibility path
  (`src/micro/tdx_downloader.py`) remains available and the real adapter
  implementation is explicitly deferred.
- ADR-0007: CORS remains permissive, but the FastAPI process is loopback-only
  (`127.0.0.1:8901`) and the deferral explicitly forbids non-loopback exposure
  before CORS hardening and auth.

## Loaded Evidence

| Artifact | Purpose |
|---|---|
| `production/architecture-reviews/architecture-review-brief-s003-014.md` | Review brief and ruling questions |
| `docs/architecture/adr-0004-data-source-adapter-contract.md` | Data-source adapter status and promotion gate |
| `docs/architecture/adr-0007-api-surface-and-cors.md` | FastAPI / CORS status and deferral decision |
| `src/doge/infrastructure/data_source/tdx.py` | Live TDX adapter implementation state |
| `src/api/main.py` | Live FastAPI bind, CORS, and error-envelope implementation |
| `production/sprint-status.yaml` | Sprint 003 state and S003-014 dependency status |
| `production/sprints/sprint-003-verification.md` | Sprint acceptance criteria and deferred items |
| `production/milestones/verification-milestone.md` | Verification milestone governance criteria |
| `tests/unit/governance/test_adr_lifecycle_status.py` | ADR lifecycle contract expectations |
| `docs/architecture/control-manifest.md` | ADR lifecycle and layer-gate control rules |

Validation command run:

```powershell
python -m pytest tests\unit\governance tests\unit\layer_gates tests\contract\test_api_error_envelope.py tests\test_yfinance_adapter.py -q
```

Result: `72 passed`.

## ADR-0004 Ruling

Question: may ADR-0004 stay Proposed through Sprint 003 closure?

Answer: **Yes, with CONCERNS.**

Rationale:

- `IMarketDataSource` exists and `YFinanceDataSource` is implemented and tested.
- `src/doge/infrastructure/data_source/tdx.py` still raises
  `NotImplementedError` from both `download_kline` and
  `get_latest_market_date`.
- The unfinished TDX adapter work is explicitly documented in ADR-0004,
  `production/milestones/verification-milestone.md`, and the Sprint 003 plan.
- The operator still has the legacy `src/micro/tdx_downloader.py` path available.
- Promoting ADR-0004 to Accepted now would overstate the architecture state,
  because the TDX half of the adapter contract is not implemented.

Decision:

- ADR-0004 remains **Proposed**.
- Sprint 003 closure is not blocked by ADR-0004.
- Post-Verification must retain a TDX adapter migration story before ADR-0004
  may be promoted to Accepted.

Promotion gate remains:

1. Implement `TDXDataSource` without `NotImplementedError`.
2. Migrate or thin-wrap `src/micro/tdx_downloader.py` through the port.
3. Add deterministic tests or an explicitly documented live-smoke evidence path
   for the TDX adapter.
4. Re-run governance tests and update ADR lifecycle status only after the gate
   is met.

## ADR-0007 Ruling

Question: may ADR-0007 stay Proposed through Sprint 003 closure?

Answer: **Yes, with CONCERNS.**

Rationale:

- The error-envelope half of ADR-0007 is implemented:
  `src/api/main.py` has global `HTTPException` and catch-all exception handlers,
  and the regression is covered by `tests/contract/test_api_error_envelope.py`.
- The CORS hardening half is not implemented:
  `src/api/main.py` still uses `allow_origins=["*"]`.
- The current deployment boundary is loopback-only:
  `uvicorn.run(app, host="127.0.0.1", port=8901)`.
- The permissive CORS posture is acceptable only under the loopback bind and
  local-first, single-operator assumption.
- Any non-loopback bind without prior CORS tightening and auth would invalidate
  this ruling.

Decision:

- ADR-0007 remains **Proposed**.
- Sprint 003 closure is not blocked by ADR-0007.
- The project must not claim CORS is production-hardened.
- Non-loopback FastAPI exposure remains forbidden until CORS hardening and auth
  are implemented.

Promotion gate remains:

1. Either implement explicit CORS allow-list hardening, or write a separate
   strengthened-loopback-guarantee decision that is accepted by architecture
   review.
2. Add auth before any non-loopback bind is allowed.
3. Re-run API contract and governance tests.

## Sprint 003 Closure Ruling

Overall Sprint 003 closure is **approved with CONCERNS** for the architecture
review portion.

This review satisfies S003-014's acceptance criterion:

> Fresh session runs `/architecture-review`; ADR-0004/0007 states finalized with
> documented rationale.

Finalized state:

| ADR | Finalized Sprint 003 State | Closure Decision |
|---|---|---|
| ADR-0004 | Proposed with TDX adapter deferral rationale | Does not block Sprint 003 closure |
| ADR-0007 | Proposed with loopback-only CORS deferral rationale | Does not block Sprint 003 closure |

## Conditions

Sprint 003 may only close under this review if the following remain true:

1. FastAPI remains bound to `127.0.0.1` by default.
2. No document or story claims ADR-0004 or ADR-0007 is Accepted.
3. No document claims CORS is production-hardened.
4. TDX adapter migration remains tracked as post-Verification work.
5. Governance tests continue to pin ADR-0004 and ADR-0007 as Proposed until
   their promotion gates are actually met.

## Non-Blocking Notes

- `src/api` no longer has direct `sqlite3.connect`, `import sqlite3`, or
  `connect_duckdb` matches in the current code scan. Some older traceability
  text still describes this as outstanding debt; that text is stale relative to
  S003-003 and should be cleaned up during the final Sprint 003 closure rollup
  or the next architecture-traceability refresh.
- This was a focused review for S003-014, not a full CDD-wide traceability
  rebuild. No TR IDs were added, removed, renumbered, or deprecated.

## Required Follow-Up

| Item | Owner | Timing |
|---|---|---|
| Implement real `TDXDataSource` adapter and migrate/thin-wrap `tdx_downloader.py` | data-source / architecture owner | Post-Verification |
| Harden FastAPI CORS or record strengthened loopback guarantee | API / security owner | Before any non-loopback bind |
| Keep ADR-0004 and ADR-0007 Proposed in governance tests | lead-programmer | Until promotion gates land |

