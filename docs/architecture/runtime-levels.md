# Agent Runtime Levels

> Runtime maturity is authoritative in `docs/progress/runtime-maturity.yaml`.
> Current posture remains `production_ready: false`,
> `stable_declaration: forbidden`, and Level 3 `experimental`.

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

Level 3 remains experimental. SDK/Web progress does not imply Stable or
Production Ready until all required runtime, external, provider, packaging, and
operator gates are closed.

## Preferred Stack

ADR-0024 defines the preferred new platform path:

```text
process roots -> persisted runtime -> /v1/* routes -> SDK/Web/CLI clients
```

Compatibility surfaces remain available while migration evidence is gathered:

| Surface | Status |
|---------|--------|
| Legacy `/api/*` | Compatibility with deprecation headers. |
| `doge.application.composition` | Compatibility shim for old imports. |
| In-memory runtime | Demo/test only. |
| PyQt dashboard | Legacy-maintained local surface. |

Sprint E adds bounded-context ownership and scenario navigation gates, but does
not promote any runtime level.

## Maturity Rule

A level's maturity label can only be promoted when every required gate in
`docs/progress/runtime-maturity.yaml` is satisfied by code and tests.

## Promotion Review Status - 2026-06-21

Sprint 015 added local release-quality evidence for performance, Kimi retry,
Research Agent accessibility, and soak readiness. The review verdict is no
Stable promotion. Remote CI and one-hour local daemon soak evidence later
landed, but live Kimi smoke, browser/manual reconnect evidence,
screen-reader manual evidence, citation-quality evaluation, and production data
gates remain open.
