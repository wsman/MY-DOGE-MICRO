# Architecture Review — Sprint 004 (Release clean-PASS prep)

> **Date**: 2026-06-14  
> **Scope**: Sprint 004 ADR promotions + layer-gate cleanup  
> **Authority**: fresh `/architecture-review` for the Verification → Release gate  
> **Verdict**: **PASS** — 0 CONCERNS

---

## Ruling summary

| # | Question | Ruling |
|---|---|---|
| 1 | Authorize ADR-0007 strengthened-loopback-guarantee promotion to **Accepted** | **AUTHORIZED** |
| 2 | Verify ADR-0004 (already flipped to Accepted in S004-008a) | **CONFIRMED sound** |
| 3 | Rule on `TDXDataSource.connect(self, market="cn")` signature extension | **ACCEPTABLE** with documentation note |
| 4 | Confirm §6 layer-gate cleanup green | **CONFIRMED** (0 grep hits) |

---

## 1. ADR-0007 — strengthened-loopback-guarantee promotion

### Evidence reviewed

- `src/api/main.py:119-134` — `_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}` and `_resolve_bind_host()` fail-closed assertion. Any non-loopback `DOGE_BIND_HOST` raises `AssertionError` with the ADR-0007 promotion-gate message before `uvicorn.run` is reached.
- `src/api/main.py:35-40` — `CORSMiddleware` retains `allow_origins=["*"]`, explicitly justified by the loopback-only bind.
- `tests/test_api_loopback_guarantee.py` — 6 tests covering default host, all loopback variants, non-loopback IP, and non-loopback hostname.
- Full suite: **568 passed, 2 skipped, 0 failed**.

### Rationale

The original ADR-0007 promotion gate required either:

- (a) tightening CORS to an explicit localhost allow-list and gating non-loopback binds on it, or
- (b) an explicit strengthened-loopback-guarantee decision.

Sprint 004 chose path (1b) per operator decision. The implementation makes the loopback guarantee **fail-closed** (not default-dependent) by introducing `DOGE_BIND_HOST` and asserting its value before the server starts. The permissive CORS posture is therefore safe under the local-first, single-operator deployment model and unsafe only if an operator deliberately bypasses the assertion.

This satisfies the ADR-0007 promotion condition recorded at ADR-0007:46-49.

**Authorization granted**: S004-008b may flip ADR-0007 Status to `Accepted` using the phrase **"loopback-guaranteed"** (NOT "production-hardened", per S003-014 cond 3).

---

## 2. ADR-0004 — TDX adapter promotion verification

### Evidence reviewed

- `src/doge/infrastructure/data_source/tdx.py` — full `TDXDataSource` implementation of `IMarketDataSource`: `connect`, `disconnect`, `is_connected`, `download_kline`, `get_latest_market_date`.
- No `NotImplementedError` remains in the adapter.
- `tests/test_tdx_adapter.py` — 26 network-free tests covering port conformance, lifecycle, CN/US kline paths, ticker remap, retry exhaustion, empty-result degradation, latest-date success/failure, and opentdx-absent regression.
- `src/micro/tdx_downloader.py` is thin-wrapped as a CLI shim that constructs the adapter (ADR-0004 Migration Plan step 4).
- Lazy `opentdx` import inside method bodies preserves the optional-dependency tolerance established in commit `5fd26ee`.

### Ruling

ADR-0004's S002-011 promotion gate (TDX adapter implemented without `NotImplementedError`) is met. The S004-008a Status flip to `Accepted` is **confirmed sound**.

---

## 3. TDX `connect(self, market="cn")` signature

### Observation

`IMarketDataSource.connect` declares:

```python
@abstractmethod
def connect(self) -> None: ...
```

`TDXDataSource.connect` declares:

```python
def connect(self, market: str = "cn") -> None: ...
```

This is Liskov-compatible in Python: a caller invoking `ds.connect()` on either the port or the adapter gets a valid call. All port-conformance tests pass.

### Why it is acceptable

- TDX is a **stateful, market-specific** TCP source (unlike stateless yfinance). Binding the server family at connect time is a legitimate adapter-level concern.
- The default value (`"cn"`) preserves the port contract for generic callers.
- The adapter is constructed and connected by code that knows it is using TDX (composition root, CLI shim), so the extra parameter is not a surprise.
- No caller has been observed that relies on the stricter `connect(self) -> None` signature in a way that would break.

### Recommendation

Add a short note to `docs/architecture/adr-0004-data-source-adapter-contract.md` (or to `design/cdd/data-sources.md`) documenting that adapter signatures may add source-specific optional parameters provided they remain callable via the port contract. This is **not blocking**.

---

## 4. §6 layer-gate cleanup

### Evidence

```bash
grep -rnE "import sqlite3|import duckdb|sqlite3.connect|duckdb.connect" src/api src/doge/interfaces src/interface
# ZERO hits
```

The only prior RED site (`src/doge/interfaces/mcp/tools/query_stock.py:4,92`) was removed in S004-003. `src/api/routers/notes.py` now depends on `deps.get_note_repository` rather than `ai_analysis.stock_notes` (S004-002). `src/api/routers/scan.py` uses the `SQLiteConnection` adapter, which is allowed by ADR-0001 §4.3.

### Ruling

§6 layer gate is **GREEN**.

---

## Validation checklist

- [x] ADR-0007 loopback guarantee reviewed and promotion authorized.
- [x] ADR-0004 TDX adapter implementation reviewed and Accepted status confirmed.
- [x] TDX `connect(self, market)` signature ruled acceptable.
- [x] §6 layer gate grep returns zero hits.
- [x] Full pytest suite green (568 passed / 2 skipped / 0 failed).

---

## Output authorization

This review authorizes the following next steps:

1. **S004-008b**: flip `docs/architecture/adr-0007-api-surface-and-cors.md` Status to `Accepted` and update `tests/unit/governance/test_adr_lifecycle_status.py`.
2. **Fresh `/gate-check`**: run Verification → Release for clean PASS.

---

## Related artifacts

- Brief: `production/architecture-reviews/architecture-review-brief-s004.md`
- Prior review: `production/architecture-reviews/architecture-review-s003-014-2026-06-13.md`
- ADR-0004: `docs/architecture/adr-0004-data-source-adapter-contract.md`
- ADR-0007: `docs/architecture/adr-0007-api-surface-and-cors.md`
- Loopback code: `src/api/main.py`, `tests/test_api_loopback_guarantee.py`
- TDX adapter: `src/doge/infrastructure/data_source/tdx.py`, `tests/test_tdx_adapter.py`
- Notes port: `src/doge/core/ports/repository.py`, `src/doge/infrastructure/database/repositories.py`, `tests/unit/doge/test_note_repository.py`
- Governance test: `tests/unit/governance/test_adr_lifecycle_status.py`
