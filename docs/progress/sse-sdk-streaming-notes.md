# SSE And SDK Streaming Notes

Generated: 2026-06-21

Sprint 011 moves Research Agent client continuation from polling toward v1 SSE.

## Backend Contract

- `GET /v1/runs/{run_id}/stream` emits SSE events with `id` equal to the event
  sequence.
- Clients may send `Last-Event-ID` to replay from a checkpoint.
- Streams close after display-ready events such as approval request,
  artifact creation, error, or cancellation.

## Web Client

- `web/src/api/agent.ts` now streams newly created runs and queued approval
  continuations through `dogeClient.runs.stream()`.
- The Pinia store API stays stable: it still receives a final `AgentRun` and
  exposes approvals/artifacts the same way.
- Targeted tests cover both create and approval paths.

## TypeScript SDK

- `runs.stream(runId, lastEventId)` remains backward-compatible.
- `runs.stream(runId, { lastEventId, reconnect, maxReconnects, backoffMs })`
  adds bounded reconnect/backoff.
- Reconnect retries network/stream failures only; API errors are surfaced.

## Python SDK

- Sync `runs.stream()` now supports bounded reconnect/backoff for `httpx`
  transport errors.
- `AsyncDogeClient` exposes async sessions, runs, documents, and async SSE
  iteration.
- `Last-Event-ID` is preserved on reconnect for both sync and async paths.

## Current Limits

- Clean stream completion is treated as complete; reconnect is for network or
  stream exceptions.
- Browser-runtime TypeScript SDK reconnect/replay evidence exists at
  `production/qa/evidence/manual/browser-sdk-sse-reconnect-2026-06-22.md`.
- Full Research Agent browser/manual reconnect evidence against a running
  daemon is still pending.
- Remote CI is still pending for this sprint.
