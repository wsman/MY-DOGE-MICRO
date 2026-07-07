# ADR-0007: API Surface and CORS

## Status

Accepted (S004-008b, 2026-06-14)

> **Promotion authorized by fresh `/architecture-review`**
> (`production/architecture-reviews/architecture-review-s004-2026-06-14.md`).
> The strengthened-loopback-guarantee path (1b) is now implemented and verified:
> `src/doge/interfaces/api/main.py` asserts a fail-closed loopback bind via
> `DOGE_BIND_HOST`; `tests/compat/test_api_loopback_guarantee.py` covers the guarantee;
> and the full suite is green (568 passed / 2 skipped / 0 failed). CORS remains
> `allow_origins=["*"]`, safe only under this loopback guarantee; any future
> non-loopback bind requires CORS allow-list hardening + auth first. The posture
> is **loopback-guaranteed**, not "production-hardened".

## Deferral Decision (S003-013, 2026-06-12) — CLOSED by S004-008b

**Decision.** CORS hardening remains deferred through the Verification stage, and
ADR-0007 intentionally stayed **Proposed** through Verification. Sprint 004 chose
path (1b) — a strengthened loopback guarantee — rather than the original
CORS-hardening path. The deferral is now closed by promotion to **Accepted**.

**Security argument.** The FastAPI server binds to `127.0.0.1:8901`
(`src/doge/interfaces/api/main.py`) via the `_resolve_bind_host()` fail-closed assertion; no
remote client can reach it in the default deployment. The platform is
single-operator, local-first, and has **no authentication by design**
(local-first constraint — see §Context/Constraints). Therefore the current
`allow_origins=["*"]` (Decision 2; `main.py:35-40`) is acceptable for the current
loopback-only scope. The permissiveness is safe **only because** of the loopback
bind; it is not safe under any other bind.

**Promotion gate.** A non-loopback `bind_host` (e.g. `0.0.0.0`) **REQUIRES**,
before it may be set: (a) tightening CORS to an explicit localhost allow-list
(Migration Plan step 3 / Alternative 1), AND (b) adding auth (Alternative 2) —
auth FIRST. Promotion of ADR-0007 from Proposed to Accepted was gated on the
CORS-hardening story landing OR an explicit strengthened-loopback-guarantee
decision, signed off by **Sprint 004 fresh `/architecture-review`** — this
sign-off is recorded in
`production/architecture-reviews/architecture-review-s004-2026-06-14.md`.

**Cross-reference.** ADR-0007 is now **Accepted**. No story may claim
"CORS is production-hardened" — the posture is explicitly
**loopback-guaranteed**.

## Date

2026-06-12

## Last Verified

2026-06-12

## Decision Makers

lead-programmer, python-specialist (reverse-documentation of the brownfield
FastAPI service in `src/doge/interfaces/api/`).

## Summary

This ADR records the API surface of the local-first FastAPI service (the
canonical 94-route table across legacy `/api/*` routers and daemon
`/v1/*` routes bound to `127.0.0.1:8901`), the decision to ship
`CORSMiddleware` with
`allow_origins=["*"]` justified by the loopback bind + local-first scope, and
the stance that error responses must converge on a stable, non-leaking
envelope for explicit and otherwise-unhandled internal errors.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Engine** | N/A — product project (no game engine). Framework: FastAPI 0.123.8 / Uvicorn 0.38.0 / Pydantic 2.12.4 / sse-starlette 3.0.3. |
| **Domain** | API / Interface layer (`src/doge/interfaces/api/`). |
| **Knowledge Risk** | LOW — FastAPI CORS middleware and HTTPException are stable, long-standing APIs well within training data. |
| **References Consulted** | `docs/reference/python/` (pinned stack per `standards/technical-preferences.md`); `.claude/rules/api-code.md`; live source `src/doge/interfaces/api/main.py`. |
| **Post-Cutoff APIs Used** | None. |
| **Verification Required** | None. |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0001 (brownfield-clean-architecture — establishes the layer rules and forbidden patterns this ADR's remediation items reference), ADR-0002 (centralized-configuration — the `get_settings()` target for the `_PROJECT_ROOT` remediation). |
| **Enables** | Module #9 `fastapi-service` CDD; the future CORS-hardening story; the error-envelope remediation story. |
| **Blocks** | No story is blocked from *starting*; stories that claim "CORS is production-hardened" cannot be marked Done until the corresponding ACs in the fastapi-service CDD §8 are satisfied. |
| **Ordering Note** | The CORS hardening and error-envelope work can proceed independently of each other; both are independent of the repository-routing migration (ADR-0001/#12). |

## Context

### Problem Statement

The FastAPI service (`src/doge/interfaces/api/main.py` + legacy `/api/*` and daemon `/v1/*` routers) is the local-first HTTP
interface every UI consumer (Vue web console, PyQt desktop) calls. Three
decisions needed to be made and recorded so that (a) consumers have a stable,
enumerated contract to build against; (b) the permissive CORS configuration is
explicitly justified rather than an accident; and (c) the error-leak
anti-pattern (`except Exception as e: raise HTTPException(500, str(e))`) has a
documented target state instead of being silently propagated into every new
handler.

### Current State

- The app binds to `127.0.0.1:8901` (`src/doge/interfaces/api/main.py`) and registers legacy
  routers under `/api/*`, daemon/platform routes under `/v1/*`, and health helpers.
  The full 94-route table is enumerated in `docs/API.md` and summarized in the
  fastapi-service CDD §4.1.
- `CORSMiddleware` is added with `allow_origins=["*"]`, `allow_methods=["*"]`,
  `allow_headers=["*"]` (`main.py:22-27`). The inline comment
  "仅 localhost, 无安全风险" records the local-first intent but the decision
  was never captured in an ADR.
- Error handling is inconsistent: the `data` kline handler and five of the six
  `notes` handlers wrap their body in `except Exception as e: raise
  HTTPException(500, str(e))` (`data.py:141-142`; `notes.py:31-32,48-49,
  58-59,67-68,76-77`), leaking internal exception messages into the HTTP
  `detail`. This violates `.claude/rules/api-code.md` ("Do not leak secrets,
  internal stack traces, database identifiers, or implementation-only fields").
  The `macro`/`analysis` read handlers do not catch and rely on FastAPI's
  default 500. The `notes` DELETE handler is the only notes handler that does
  not swallow (it returns explicit `200`/`404`).
- Every router recomputes `_PROJECT_ROOT` (ADR-0001 forbidden pattern) and
  opens SQLite/DuckDB directly (ADR-0001 `direct_sqlite_import_in_interface`).

### Constraints

- **Local-first**: the platform is single-operator, runs on the operator's
  desktop, and binds to loopback by default. No remote clients are in scope.
  This is the load-bearing constraint behind the CORS decision.
- **No auth**: consistent with local-first, the API has no authentication.
  api-code.md's "auth failure" test case is therefore N/A.
- **Brownfield**: the service already exists and is consumed by UIs; the
  surface cannot be renamed wholesale without coordination.
- **FastAPI/Pydantic v2**: route validation, `Query` constraints, and
  `HTTPException` are the boundary primitives; the decision must use them.

### Requirements

- A single, auditable enumeration of every product route (method, path,
  router, purpose, file:line) so consumers and tests have a stable contract.
- A documented justification for the permissive CORS policy that is honest
  about its limits and records the hardening option.
- A target error shape that is stable, testable, and non-leaking, with the
  current leak pattern explicitly tracked as tech debt (not blessed).
- Contract tests covering every endpoint (api-code.md: success, validation
  failure, edge case) — delivered as BUG E in the fastapi-service CDD.

## Decision

1. **API surface** — the 96 HTTP routes enumerated in `docs/API.md` and
   summarized in fastapi-service CDD §4.1 are the canonical contract. Any new
   route requires a docs/CDD update and a contract test. The OpenAPI
   auto-generated routes (`/openapi.json`, `/docs`, `/redoc`) are
   infrastructure, not product endpoints.

2. **CORS** — keep `allow_origins=["*"]` for the local-first deployment
   **because** the server binds to `127.0.0.1` (`main.py:67`) and no remote
   client can reach it in the default configuration. The Vue web console
   (Module #11) and the PyQt desktop (Module #10) are same-machine consumers.
   Record that this is safe *only* under the loopback bind, and that binding
   to a non-loopback interface REQUIRES tightening CORS (and adding auth)
   first — see Migration Plan.

3. **Error shape** — adopt a single stable, non-leaking envelope as the
   target:

   ```json
   {"error": {"code": "<stable-code>", "message": "<operator-safe message>"}}
   ```

   implemented via a single `@app.exception_handler(Exception)` (and a
   corresponding handler for `HTTPException`). The raw exception detail is
   **logged server-side, never returned**. The current
   `except Exception as e: raise HTTPException(500, str(e))` pattern is
   **tracked tech debt**, not a contract: until the handler lands, contract
   tests on those paths assert the status code only (not the leaked
   message).

### Architecture

```
                    +-----------------------------+
   browser/desktop  |  FastAPI app (127.0.0.1:8901)|
   (localhost)      |  CORSMiddleware  allow=*    |
        |           |  6 routers + 2 helpers      |
        +---------> |  JSON  +  SSE (scan/macro)  |
                    |  ExceptionHandler (target)  |
                    +--------------+--------------+
                                   |
                 +-----------------+-----------------+
                 |                 |                 |
           IStockRepository  IReportRepository   (legacy direct
              (target)           (target)        sqlite/duckdb —
                                                current state)
```

### Key Interfaces

```python
# Target error envelope (not yet implemented)
@app.exception_handler(Exception)
async def _unhandled(request, exc) -> JSONResponse:
    logger.exception("unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error",
                           "message": "internal server error"}},
    )

@app.exception_handler(HTTPException)
async def _http_exc(request, exc) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": str(exc.status_code),
                           "message": exc.detail}},
    )
```

### Implementation Guidelines

- Do NOT remove the existing `HTTPException(400/404/409, ...)` sites — they
  carry operator-safe fixed strings and become the `message` field under the
  new envelope.
- Replace ONLY the `except Exception as e: raise HTTPException(500, str(e))`
  sites (`data.py:141-142`; `notes.py:31-32,48-49,58-59,67-68,76-77`) by
  deleting the `try/except` wrapper and letting the global handler catch the
  exception.
- Keep the SSE error events (`scan.py:222`, `macro.py:117`) — they are
  in-band stream payloads, not HTTP error responses, but should adopt a
  stable `code` field alongside `message` for symmetry (open question, not
  gating).

## Alternatives Considered

### Alternative 1: Tighten CORS now to an explicit localhost allow-list

- **Description**: set `allow_origins=["http://localhost:5173",
  "http://127.0.0.1:5173", <tauri origin>]` immediately.
- **Pros**: defense-in-depth; removes the implicit dependency on the
  loopback bind for safety.
- **Cons**: requires knowing every origin the Vue dev server and the
  Tauri/desktop shell use today, and breaks if a new dev port is introduced;
  adds friction for a single-operator local tool.
- **Estimated Effort**: small code change, but requires a config knob
  (env/list) that does not yet exist.
- **Rejection Reason**: not rejected — recorded as the **hardening target**
  (Migration Plan step 3). The local-first constraint makes `*` safe enough
  for the current scope; tightening is a follow-on, not a prerequisite.

### Alternative 2: Add token auth now

- **Description**: require a bearer token on every route.
- **Pros**: enables binding to non-loopback interfaces safely.
- **Cons**: contradicts the local-first, no-auth design; adds operator
  burden (token management) for a tool with no remote clients.
- **Estimated Effort**: medium (middleware + token issuance + every test).
- **Rejection Reason**: out of scope for local-first. Revisit only if the
  deployment model changes to include remote clients.

### Alternative 3: Keep the `str(e)` leak and document it as accepted

- **Description**: bless the current `500 str(e)` as the error contract.
- **Pros**: zero work.
- **Cons**: violates api-code.md ("Do not leak ... internal stack traces ...
  implementation-only fields"); leaks DB paths and SQL fragments to any UI
  that renders the detail; untestable as a stable contract.
- **Estimated Effort**: none.
- **Rejection Reason**: explicitly rejected. The leak is tracked tech debt
  with a target envelope; it is not the contract.

## Consequences

### Positive

- The route table is now a single auditable enumeration (CDD §4.1) that
  consumers and tests cite.
- The CORS rationale is recorded, so a future reviewer sees *why* `*` is
  acceptable and *when* it must change.
- The error-leak pattern has a named target shape and is no longer silently
  propagated.
- BUG E (router contract tests) is delivered, satisfying the api-code.md
  gate for the FastAPI service.

### Negative

- `allow_origins=["*"]` remains permissive until the hardening story lands;
  anyone who (mis)configures `bind_host=0.0.0.0` before tightening CORS
  exposes the API to the LAN. Mitigated by documenting the coupling in §7
  of the CDD and in the Migration Plan below.
- The error envelope is target-only; until it lands, the `str(e)` leak
  persists and contract tests must avoid asserting on the message.

### Neutral

- The OpenAPI auto-routes (`/docs`, `/redoc`, `/openapi.json`) are available
  in every environment by default — convenient for local dev, would be
  disabled behind a flag in a multi-tenant deployment (not applicable here).

## Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| Operator binds to non-loopback before tightening CORS | LOW (local-first default) | HIGH (LAN exposure, no auth) | Document the coupling (CDD §7, Migration Plan); gate a non-loopback bind on the CORS + auth hardening story. |
| A new handler copies the `str(e)` leak pattern | MEDIUM | MEDIUM (more leak surface) | Add the global exception handler so the pattern is no longer needed; lint rule / code review check. |
| Route-table drift (new route added without CDD/test) | MEDIUM | LOW (contract gap) | Require a CDD §4.1 row + contract test for every new route (api-code.md). |
| SSE error payload leaks `str(e)` into the stream | MEDIUM | LOW (in-band, not HTTP) | Adopt a stable `code` field in SSE error events (open question, non-gating). |

## Performance Implications

| Metric | Before | Expected After | Budget |
|--------|--------|---------------|--------|
| Per-request JSON overhead | baseline | unchanged (envelope is same order of size) | n/a |
| CORS preflight latency | baseline (permissive, few preflights) | slightly higher if tightened (explicit origins still few) | < 50ms |
| Error-path latency | baseline | +1 logger.exception call | < 5ms added |

No meaningful performance impact. CORS and the error envelope are not on the
hot path.

## Migration Plan

1. **Error envelope (do first)** — add the two exception handlers in
   `src/doge/interfaces/api/main.py`; delete the `try/except Exception as e: raise
   HTTPException(500, str(e))` wrappers in `data.py` and `notes.py`. Update
   `tests/test_api_routers.py` to assert the new envelope shape on the
   previously-leaking paths. Verify: full suite green; no `detail` field
   contains `str(e)` of an internal exception.
2. **Repository routing (parallel, owned by #12)** — replace direct
   `sqlite3`/`connect_duckdb` calls with `IStockRepository`/`IReportRepository`
   reads; remove `_PROJECT_ROOT` per router in favor of `get_settings()`. Out
   of scope for this ADR's implementer; referenced because it removes the
   `direct_sqlite_import_in_interface` violations that make the leak worse
   (leaked SQL/paths).
3. **CORS hardening (do last, only if needed)** — introduce an
   `APIConfig.cors_origins` list on `Settings()` (defaulting to the explicit
   localhost origins used by the Vue dev server and the Tauri shell); replace
   `["*"]` in `main.py:24`. Gating condition: must land BEFORE any change to
   `bind_host` away from `127.0.0.1`.

**Rollback plan**: each step is independently revertible. The error-envelope
handlers can be removed and the old `try/except` restored; CORS can be
returned to `["*"]`; repository routing is backward-compatible by definition.

## Validation Criteria

- [x] The fastapi-service CDD §4.1 route table matches the routes FastAPI
  reports at startup (`[r.path for r in app.routes]`) for the 96 HTTP
  routes, guarded by `tests/contract/test_api_doc_route_coverage.py`.
- [ ] `tests/test_api_routers.py` is green and covers every endpoint
  (success + validation failure + edge case); the no-auth case is documented
  as intentionally skipped. (DONE — 57 passed as of 2026-06-12.)
- [x] After the error-envelope migration: no response body on any path
  contains the raw `str(e)` of an internal exception (regression assertion).
  **(DONE — S002-009.)** The two global handlers (`@app.exception_handler(
  HTTPException)` + `@app.exception_handler(Exception)`) are registered in
  `src/doge/interfaces/api/main.py`; the six `try/except Exception as e: raise HTTPException(
  500, str(e))` wrappers are removed from `data.py:get_kline` and the five
  `notes.py` handlers. The stable `code` convention is a **string enum**
  (`bad_request` / `not_found` / `conflict` / `unprocessable` /
  `internal_error`, with an `http_{status}` fallback for unmapped codes)
  rather than the illustrative `str(exc.status_code)` pseudocode shown in the
  Key Interfaces block above — the string enum was chosen so the S002-010 SSE
  client can branch on `error.error.code`. The raw exception is logged
  server-side via `logging.getLogger("doge.api").exception(...)` and is never
  returned. The BLOCKING contract regression is
  `tests/contract/test_api_error_envelope.py`. FastAPI's default 422
  `RequestValidationError` handler is intentionally left as-is (out of scope
  for S002-009); S002-011 owns any follow-on.
- [ ] After the CORS hardening: `allow_origins` is an explicit list and a
  non-loopback `bind_host` is gated on it.
- [x] This ADR is promoted from Proposed to Accepted. The strengthened-loopback-guarantee path (1b) was signed off by Sprint 004 fresh `/architecture-review` (`production/architecture-reviews/architecture-review-s004-2026-06-14.md`). Posture is **loopback-guaranteed**, not "production-hardened".

## CDD Requirements Addressed

| CDD Document | System | Requirement | How This ADR Satisfies It |
|-------------|--------|-------------|--------------------------|
| `design/cdd/fastapi-service.md` | FastAPI Service (Module #9) | "Error responses must return a stable non-leaking error shape; the current 500-with-str(e) is tracked tech debt." (§8) | Records the target envelope, the global-handler implementation, and explicitly tracks the leak as tech debt (Decision 3 + Migration Plan step 1). |
| `design/cdd/fastapi-service.md` | FastAPI Service (Module #9) | "CORS currently allow_origins=[*] — document the LOCAL-FIRST justification ... AND note the option to tighten to explicit localhost origins as a hardening story." (assignment brief) | Decision 2 + Alternative 1 + Migration Plan step 3 record the rationale and the hardening option. |
| `design/cdd/fastapi-service.md` | FastAPI Service (Module #9) | "The full route table (method, path, router, purpose, file:line) as Contracts." (assignment brief) | Decision 1 blesses the CDD §4.1 enumeration as canonical. |
| `.claude/rules/api-code.md` | Product API rules | "Error responses must be stable and testable ... Do not leak ... internal stack traces ... Every endpoint must have contract or integration tests." | Decision 3 + BUG E test suite (delivered) satisfy the test gate and define the stable-shape target. |

## Related

- [ADR-0001](adr-0001-brownfield-clean-architecture.md) — forbidden patterns this ADR's remediation items reference (`direct_sqlite_import_in_interface`, `_PROJECT_ROOT_recalculation`).
- [ADR-0002](adr-0002-centralized-configuration.md) — the `get_settings()` target for the per-router `_PROJECT_ROOT` removal.
- `design/cdd/fastapi-service.md` — the Module #9 CDD this ADR serves; §4.1 route table, §8 acceptance criteria, §9 integration requirements.
- `src/doge/interfaces/api/main.py` — the live application construction (app, CORS, routers, bind).
- `src/doge/interfaces/api/routers/{scan,data,notes,macro,analysis,config}.py` — the six routers.
