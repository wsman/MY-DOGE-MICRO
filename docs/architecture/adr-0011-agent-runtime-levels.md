# ADR-0011: Agent Runtime Levels

## Status

Accepted

## Date

2026-06-21

## Last Verified

2026-06-21

## Decision Makers

lead-programmer, python-specialist

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python 3.10+, FastAPI, SQLite, Server-Sent Events, Python SDK, TypeScript SDK |
| **Domain** | Research Copilot agent runtime, daemon gateway, SDK clients |
| **Knowledge Risk** | MEDIUM — daemon event replay and SDK streaming are project-specific contracts even though FastAPI/SSE/SQLite are established technologies. |
| **References Consulted** | `docs/architecture/runtime-levels.md`, `docs/progress/runtime-maturity.yaml`, `design/cdd/research-copilot-agent-runtime.md`, `design/cdd/document-evidence-pipeline.md`, `design/cdd/sdk-daemon-client-interfaces.md` |
| **Post-Cutoff APIs Used** | No vendor SDK is frozen by this ADR; Kimi file/vision use remains behind adapter boundaries. |
| **Verification Required** | CLI/session tests, daemon worker + SSE tests, SDK contract tests, and maturity-gate evidence in `docs/progress/runtime-maturity.yaml`. |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0001 (layering/ports), ADR-0002 (runtime configuration), ADR-0007 (loopback API posture), ADR-0008 (web client architecture). |
| **Enables** | Module #13 Research Copilot Agent Runtime, Module #14 Document Evidence Pipeline, Module #15 SDK And Daemon Client Interfaces. |
| **Blocks** | Any README, release note, SDK doc, or CDD claim that a runtime level is production-ready while the required maturity gates are incomplete. |
| **Ordering Note** | Level 1/2/3 may be implemented in slices, but maturity labels are controlled by `docs/progress/runtime-maturity.yaml`, not by the presence of routes or SDK packages alone. |

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

All levels share the same kernel concepts: session, turn, run, execution
context, event, tool, model, artifact, approval.

`RunExecutionContext` is the typed boundary for one runtime step. It carries
the validated `ModelPolicy`, trusted identity snapshot, request id, and
workflow/template metadata so model routing, context building, tool execution,
and audit metadata do not need to infer execution context from ad hoc
`ModelPolicy` fields.

## Consequences

- `agent_state.db` is the dedicated local persistence store for agent runtime
  state.
- CLI and daemon paths must use repository-backed runtime code instead of the
  in-memory demo adapter.
- Runtime code should pass `RunExecutionContext` explicitly through model
  routing, prompt/context assembly, tool execution, and audit seams.
- Web feature additions are frozen until the v1 runtime contract has satisfied
  the required maturity gates.

## Performance Implications

- Level 1 embedded CLI avoids HTTP overhead and is suitable for local scripted
  runs, but still persists state to SQLite.
- Level 2 daemon runs add worker/event-bus overhead and must keep SSE replay
  bounded by persisted event pagination or client-side cursoring.
- Level 3 SDK clients add retry/reconnect behavior; clients must avoid
  duplicate event rendering when `Last-Event-ID` replay is used.
- Document and evidence context can grow quickly; runtime tools should page or
  select evidence rather than loading all chunks into every turn.

## CDD Requirements Addressed

| TR | CDD | Requirement |
|---|---|---|
| TR-047 | `design/cdd/research-copilot-agent-runtime.md` | Runtime levels share session/turn/run/event/tool/model/artifact/approval concepts and remain maturity-gated. |
| TR-048 | `design/cdd/research-copilot-agent-runtime.md` | Level 1 CLI sessions persist state locally without HTTP dependency. |
| TR-049 | `design/cdd/research-copilot-agent-runtime.md`, `design/cdd/sdk-daemon-client-interfaces.md` | Level 2 daemon gateway exposes v1 sessions/runs/SSE/approval/cancel/artifact routes. |
| TR-050 | `design/cdd/sdk-daemon-client-interfaces.md` | SDK and daemon clients remain experimental until promotion gates pass. |
| TR-051 | `design/cdd/document-evidence-pipeline.md` | Document upload metadata is preserved locally. |
| TR-052 | `design/cdd/document-evidence-pipeline.md` | Pages, chunks, and evidence are persisted as source-backed runtime context. |
| TR-053 | `design/cdd/document-evidence-pipeline.md` | Kimi file/vision behavior stays behind provider adapters. |
| TR-054 | all three Release Follow-Up CDDs | Runtime maturity declarations are blocked while `production_ready: false`. |
