# CDD: Research Copilot Agent Runtime (Module #13)

> **Status**: In Review
> **Created**: 2026-06-21
> **Last Verified**: 2026-06-21
> **Governing ADRs**: ADR-0011, ADR-0001, ADR-0002, ADR-0007
> **Traceability**: TR-047, TR-048, TR-049, TR-054

---

## Overview

Research Copilot Agent Runtime owns the local agent kernel used by the demo
research workflow, embedded CLI sessions, daemon runs, approval flow, event
streaming, tool schemas, and run artifacts. It is split into Level 1/2/3 per
`docs/architecture/runtime-levels.md` and ADR-0011:

- Level 1: embedded CLI session (`doge session`, `doge run`) with SQLite state.
- Level 2: loopback daemon gateway with `/v1/sessions`, `/v1/runs`, SSE,
  cancellation, approval resume, and artifact/event persistence.
- Level 3: SDK/platform clients consuming the daemon contract.

This module is implemented as release-follow-up slices, not as a production
SLA. `docs/progress/runtime-maturity.yaml` remains the maturity authority.

## User Promise

An operator can run a local research copilot session without handing market or
document data to a remote service by default, inspect events/artifacts, approve
high-risk actions, and resume or cancel work through local CLI/daemon surfaces.

## Detailed Design

The runtime uses a shared kernel vocabulary: session, turn, run, event, tool,
model, artifact, approval. Level 1 executes in-process from the CLI. Level 2
wraps the same concepts behind FastAPI v1 routes and an asyncio worker. Both
levels persist state to `agent_state.db` so sessions and events survive process
restart.

Legacy `/api/agent/*` routes remain a compatibility/demo surface. The canonical
daemon contract is `/v1/*` for new clients.

## Data Model

State is persisted in local SQLite:

- sessions and turns: operator conversation and requested work.
- runs: lifecycle, status, cancellation, and resume metadata.
- events: append-only run event log and SSE replay source.
- artifacts: generated outputs with type and source metadata.
- approvals: pending/resolved approvals with decision history.

## Edge Cases

- Missing API key must degrade to an operator-visible pending/error state, not
  a process crash.
- Approval resume must be idempotent when the same approval is submitted twice.
- SSE clients may reconnect with `Last-Event-ID` and must not lose persisted
  events.
- Cancellation is best-effort and must leave a durable terminal status.

## Dependencies

- Runtime Configuration (#1) for local paths and bind settings.
- Market Data Storage (#2) and Research Insight Knowledge Base (#7) for local
  evidence and notes.
- FastAPI Service (#9) for Level 2 daemon exposure.
- Document Evidence Pipeline (#14) for uploaded document context.
- SDK And Daemon Client Interfaces (#15) for Level 3 clients.

## Configuration

- `DOGE_DB_DIR` controls local DB placement.
- `DOGE_BIND_HOST` remains loopback-only by default.
- Provider keys such as `MOONSHOT_API_KEY` are optional and must never be
  required for no-network tests.

## Integration Requirements

- CLI commands use the same repository-backed runtime code as daemon routes.
- `/api/agent/*` and `/v1/*` must keep distinct compatibility vs daemon
  contract roles.
- Tests may use fake providers and in-memory/demo adapters, but production code
  paths must keep the persistence boundary explicit.

## UI Requirements

The web surface may consume daemon SSE, run status, approvals, and artifacts,
but new UI claims must remain tied to the runtime maturity gate. A view can show
experimental capability; it must not imply production readiness while
`production_ready: false`.

## Acceptance Criteria

- [ ] TR-047 covers the Level 1/2/3 runtime level contract.
- [ ] TR-048 covers embedded CLI session persistence.
- [ ] TR-049 covers daemon gateway routes, SSE replay, cancellation, and
      approval resume.
- [ ] TR-054 blocks README/release/CDD maturity promotion while runtime gates
      remain incomplete.
- [ ] Level claims in docs match `docs/progress/runtime-maturity.yaml`.

## Open Questions

1. Which Level 2 daemon events are frozen as public SDK contract fields?
2. What live-provider smoke evidence is required before a runtime level can be
   promoted?
3. Which web workflows must stay on `/api/agent/*` until `/v1/*` is fully
   contracted?
