# Sprint 011 - Web SSE And SDK Streaming Reliability

> Stage: Release follow-up
> Duration: 2026-06-21 -> open
> Status: done with deferred browser/manual smoke
> Source roadmap: `C:\Users\Aby\.claude\plans\replicated-nibbling-pine.md`
> QA plan: `production/qa/qa-plan-sprint-011.md`

## Sprint Goal

Remove polling/reconnect gaps from Research Agent clients so approval
continuation and run status updates flow through v1 SSE.

## Must Have

| ID | Task | Status | Acceptance Evidence |
|---|---|---|---|
| S011-001 | Web Research Agent create/approval flows use v1 SSE instead of polling | done | `web/src/api/agent.ts`, `web/src/__tests__/agentApi.spec.ts` |
| S011-002 | TypeScript SDK stream reconnect/backoff | done | `packages/doge-sdk-typescript/src/client.ts`, `packages/doge-sdk-typescript/src/__tests__/client.spec.ts` |
| S011-003 | Python SDK sync stream reconnect | done | `packages/doge-sdk-python/doge_sdk/client.py`, `tests/contract/test_python_sdk.py` |
| S011-004 | Python async SDK client and stream support | done | `packages/doge-sdk-python/doge_sdk/client.py`, `packages/doge-sdk-python/doge_sdk/streaming.py`, `tests/contract/test_python_sdk.py` |
| S011-005 | Streaming notes and progress governance | done | `docs/progress/sse-sdk-streaming-notes.md`, `docs/progress/runtime-maturity.yaml`, `docs/progress/runtime-stability-followup-plan.md` |

## Deferred

| ID | Task | Status | Notes |
|---|---|---|---|
| S011-006 | Browser/manual reconnect evidence | deferred | Requires running the Web app against a daemon and manually interrupting/reconnecting the stream. Automated unit/contract tests cover client behavior. |

## Definition of Done

- [x] Web helper no longer polls after approval; it consumes `runs.stream()`.
- [x] `Last-Event-ID` is preserved on SDK reconnect.
- [x] TypeScript SDK reconnects stream failures with bounded backoff.
- [x] Python SDK sync stream reconnects network failures with bounded backoff.
- [x] Python SDK exposes `AsyncDogeClient` and async run streaming.
- [x] Full Web test/build gate green after final verification.
- [x] TypeScript SDK test/build gate green after final verification.
- [ ] Remote CI green after push.

## Verification

- `.\.venv\Scripts\python.exe -m pytest tests/contract/test_python_sdk.py -q` -> `5 passed in 0.21s`.
- `npm test -- --run src/__tests__/client.spec.ts` in `packages/doge-sdk-typescript` -> `3 passed`.
- `npm test -- --run src/__tests__/agentApi.spec.ts src/__tests__/agentStore.spec.ts` in `web` -> `4 passed`.
- `.\.venv\Scripts\python.exe -m pytest tests/ -q` -> `805 passed, 5 skipped, 11 warnings in 58.41s`.
- `npm test` in `web` -> `74 passed`.
- `npm run build` in `web` -> passed.
- `npm test` in `packages/doge-sdk-typescript` -> `3 passed`.
- `npm run build` in `packages/doge-sdk-typescript` -> passed.

## Stable Declaration

Stable declaration remains forbidden. Sprint 011 closes a local automated slice
of F3/F4, but browser/manual reconnect evidence, remote CI, RAG, financial
tools, industry report, live Kimi smoke, and release-quality gates remain open.
