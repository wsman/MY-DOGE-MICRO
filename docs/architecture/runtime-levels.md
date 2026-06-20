# Agent Runtime Levels

## Level 1 — Embedded CLI Session

`doge session` and `doge run` execute in the local process through the common
runtime kernel. State is persisted to `data/agent_state.db`. This level has no
HTTP dependency and supports scripted offline execution.

## Level 2 — Daemon Gateway

`doged serve` exposes loopback-only v1 routes. Session turns enqueue runs into
an asyncio worker. Events are persisted and published to the in-process event
bus for SSE clients with `Last-Event-ID` replay.

## Level 3 — SDK & Platform

The Python SDK and TypeScript SDK call the v1 daemon API. Web uses the
TypeScript SDK for research-agent workflows while legacy `/api/*` endpoints
remain available for existing screens.

## Stability Rule

A level is marked stable only when every required gate in
`docs/progress/runtime-maturity.yaml` is satisfied by code and tests.
