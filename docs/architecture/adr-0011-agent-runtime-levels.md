# ADR-0011: Agent Runtime Levels

## Status

Accepted

## Context

The research copilot demo started as an in-memory vertical slice. The next
runtime needs to support local CLI sessions, a loopback daemon gateway, and SDK
clients without splitting the agent state model.

## Decision

MY-DOGE defines three runtime levels:

- Level 1: embedded CLI session with SQLite persistence and no HTTP dependency.
- Level 2: daemon gateway with FastAPI v1 routes, worker-managed runs, durable
  state, live SSE, approval resume, and cancellation.
- Level 3: SDK/platform clients with Python first, TypeScript second, and a
  backend port for Direct Kimi API, scripted demo, and future Kimi Agent SDK.

All levels share the same kernel concepts: session, turn, run, event, tool,
model, artifact, approval.

## Consequences

- `agent_state.db` is the dedicated local persistence store for agent runtime
  state.
- CLI and daemon paths must use repository-backed runtime code instead of the
  in-memory demo adapter.
- Web feature additions are frozen until the v1 runtime contract is stable.
