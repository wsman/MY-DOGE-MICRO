# Epic: API & Transport Resilience

> **Epic Slug**: `ep-api-resilience`
> **Status**: Proposed
> **Created**: 2026-06-12
> **Sprint**: Sprint 002
> **Control Manifest**: 2026-06-12
> **Governing ADRs**: ADR-0007 (API Surface and CORS), ADR-0008 (Vue Web Console Architecture)
> **Source Findings**: TR-030 (error envelope), TR-036 (SSE reader contract), `vue-web-console.md` open question

## Overview

This epic hardens the two **operator-visible** reliability gaps in the API and
transport layers: (1) the FastAPI routers leak internal exception text via
`HTTPException(500, str(e))` instead of a stable non-leaking error envelope,
and (2) a dropped SSE stream that never emits a terminal `progress` event
leaves the Vue web console's scan status stuck. Both are ADR-0007/ADR-0008
follow-ups that the ADRs themselves name as open.

## Motivation

These are the items that an operator *will* hit:

- **Error-envelope leak (TR-030, ADR-0007 Decision 3)** — `fastapi-service.md §8`
  and ADR-0007 both state the contract is a stable
  `{error: {code, message}}` envelope via a global exception handler, and
  explicitly call the current `except Exception as e: raise
  HTTPException(500, str(e))` pattern *tracked tech debt, not the contract*.
  Internal stack traces and exception class names reaching the client are a
  security smell and break any client that depends on a stable error shape.
- **SSE reconnect (TR-036, vue-web-console OQ)** — `vue-web-console.md §8/§9 Q1`
  flags that the SSE reader treats `progress === -1` as error and
  `progress >= 100` as complete, but a stream that **drops** (network blip,
  server restart, proxy timeout) without either terminal event leaves the scan
  store in a perpetual "running" state. There is no timeout or reconnect
  heuristic on the client side.

Both stories are **BLOCKING-gated** per `control-manifest.md §3`: error-envelope
is an API-Contract story type (contract/integration test + schema diff review);
SSE reconnect is a Web/App-Workflow story type (E2E or interaction evidence +
accessibility check).

## Scope

### In Scope

- Introduce a global FastAPI exception handler that converges all error
  responses on `{error: {code, message}}` and never serializes raw `str(e)` or
  stack traces to the client.
- Add a stable error-code set for the documented failure modes (scan conflict
  409, scan error progress=-1, malformed input 422, internal 500) so the Vue
  client can branch on `code`, not on string matching.
- Add a client-side SSE timeout/reconnect (or a watchdog) in the Vue scan store
  so a dropped stream surfaces as a terminal error state instead of an
  indefinite "running".

### Out of Scope

- CORS hardening (TR-032 / ADR-0007 Decision 2) — tightening
  `allow_origins=['*']` to an explicit localhost list is gated on binding to a
  non-loopback interface, which is a separate deployment story. It is named in
  the control manifest but is **not** in this epic; it is a candidate for a
  later hardening sprint.
- The full scan-serialization contract (TR-031, `_scan_locks`, 409) — that
  already works; this epic only touches the *error path* of a failed scan and
  the *reconnect path* of a dropped stream.
- MCP transport reliability (governed by ADR-0006, already Accepted, 77 tests
  green) — out of scope; the MCP server has no equivalent leak.

## Stories

| Story ID | Title | TR-ID | Priority |
|----------|-------|-------|----------|
| S002-009 | Stable non-leaking API error envelope via global exception handler | TR-030 | MED |
| S002-010 | SSE reconnect / watchdog: dropped stream surfaces terminal error, not stuck "running" | TR-036 | MED |

## Dependencies

- **S002-009 → S002-010** (soft): the SSE reconnect story's client-side error
  state is cleaner if it can branch on the stable error `code` from S002-009.
  They can proceed in parallel, but sequencing S002-009 first avoids rework.
- **S002-009 → S002-013** (`ep-governance-security`): ADR-0007's promotion to
  Accepted is gated on "CORS hardening + error envelope" being genuinely done
  (per ADR-0007's own stated gating work and `architecture-traceability.md`
  §3). S002-009 closes the error-envelope half; CORS remains open, so ADR-0007
  stays Proposed after this sprint unless a CORS story is also added.

## Acceptance

- [ ] All FastAPI error responses conform to `{error: {code, message}}`; no
  response body contains raw `str(e)` or a Python stack trace — pinned by a
  contract test in `tests/test_api_routers.py` (**BLOCKING**).
- [ ] A documented error-code set exists and the Vue client branches on `code`.
- [ ] A dropped SSE stream (simulated mid-stream close) drives the Vue scan
  store to a terminal error state within a bounded watchdog window, not an
  indefinite "running" — pinned by a scanner-store interaction test
  (`web/src/stores/scanner.spec.ts`) (**BLOCKING**).
- [ ] `npm run build` and `npm test` stay green in `web/`.
