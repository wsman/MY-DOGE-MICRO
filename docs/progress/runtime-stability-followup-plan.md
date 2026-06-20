# Runtime Stability Follow-up Plan

Generated: 2026-06-21

This plan tracks the non-runtime blockers called out by the Sprint 008 stable-declaration ban. Sprint 008 closes the P0 runtime stability issues; these follow-up workstreams must be planned, implemented, and evidenced before any Runtime Level can be declared Stable.

## Stable Declaration Guardrail

No level may be marked Stable until:

- Sprint 008 P0 changes are merged.
- GitHub Actions CI is green on the merged branch.
- `docs/progress/runtime-maturity.yaml` links current evidence for every gate.
- The follow-up blockers below are either implemented with evidence or explicitly deferred by a later review.

## Follow-up Workstreams

### F1 Real CLI Attach and File Evidence

Scope:
- Replace `/attach` placeholder behavior with real file registration.
- Persist file hash, original filename, content type, size, and parsing status.
- Connect attached documents to agent context and artifact evidence.

Evidence required:
- CLI test proving `/attach <path>` persists a document record.
- API or repository test proving file metadata and hash are stored.
- Agent runtime test proving attached evidence is available to the context builder.
- User-facing runbook update.

Candidate files:
- `src/doge/interfaces/cli/commands/session.py`
- `src/doge/interfaces/api/routers/v1/documents.py`
- `src/doge/application/agent/context_builder.py`
- `tests/cli/test_cli_session.py`
- `tests/integration/test_agent_sse_stream.py`

### F2 Evidence Extraction and Citation Grounding

Scope:
- Add source-backed evidence objects for uploaded or registered documents.
- Track citation snippets/pages where available.
- Reject or flag unsupported high-risk claims.

Evidence required:
- Unit tests for evidence extraction and citation serialization.
- Eval cases that expect grounded evidence flags.
- Artifact snapshot proving memo data includes citation/evidence references.

Candidate files:
- `src/doge/core/domain/agent_models.py`
- `src/doge/application/agent/context_builder.py`
- `src/doge/application/agent/model_response_assembler.py`
- `tests/eval/cases.json`
- `tests/eval/test_run_eval.py`

### F3 Web Research Agent SSE Migration

Scope:
- Replace post-approval polling in the Web Research Agent with v1 SSE streaming.
- Preserve replay with `Last-Event-ID`.
- Surface queued/running/awaiting/completed/cancelled states without manual refresh.

Evidence required:
- Web unit tests for SSE reconnect and event replay behavior in the agent store.
- Manual or automated browser check that approval updates stream to the UI.
- API contract remains compatible with existing SDK calls.

Candidate files:
- `web/src/api/agent.ts`
- `web/src/stores/agent.ts`
- `web/src/composables/useSSE.ts`
- `web/src/__tests__/agentApi.spec.ts`
- `web/src/__tests__/agentStore.spec.ts`

### F4 SDK Auto-reconnect and Async Python SDK

Scope:
- Add Python async client support for streaming runs.
- Add SDK-level SSE reconnect/backoff behavior.
- Ensure TypeScript SDK exposes a stable streaming abstraction independent of the Web app.

Evidence required:
- Python SDK async streaming tests with reconnect.
- TypeScript SDK reconnect tests.
- Contract test against v1 stream replay using `Last-Event-ID`.

Candidate files:
- `packages/doge-sdk-python/doge_sdk/client.py`
- `packages/doge-sdk-python/doge_sdk/streaming.py`
- `packages/doge-sdk-typescript/src/client.ts`
- `packages/doge-sdk-typescript/src/streaming.ts`
- `tests/contract/test_python_sdk.py`

### F5 Multimodal and Document Parsing Pipeline

Scope:
- Define accepted file types, parser outcomes, and failure states.
- Add parsing task lifecycle for uploaded documents.
- Extend agent model messages only after evidence extraction is deterministic.

Evidence required:
- Parser unit tests for supported and unsupported file types.
- Document lifecycle API tests.
- Runtime context tests proving parser failures are visible and safe.

Candidate files:
- `src/doge/interfaces/api/routers/v1/documents.py`
- `src/doge/infrastructure/database/agent_repositories.py`
- `src/doge/application/agent/context_builder.py`
- `tests/contract/test_v1_api.py`

### F6 Release-quality Operational Gates

Scope:
- Add formal accessibility/Core Web Vitals checks for the Research Agent UI.
- Add soak test protocol for long-running daemon sessions.
- Decide whether monitoring/crash reporting remains not-applicable for local-only release.

Evidence required:
- Accessibility review artifact.
- Soak test report or scripted protocol.
- Release checklist update that records explicit applicability decisions.

Candidate files:
- `production/releases/`
- `production/session-state/active.md`
- `docs/progress/runtime-maturity.yaml`

## Recommended Sequencing

1. F1 real attach and persisted file metadata.
2. F2 evidence extraction and citation grounding.
3. F3 Web SSE migration.
4. F4 SDK reconnect and async support.
5. F5 multimodal/parser lifecycle.
6. F6 release-quality operational gates.

## Current Status

Status: follow-up planned, not implemented.

This document satisfies the Sprint 008 requirement to give the remaining non-runtime blockers their own follow-up plan. It does not mark any level Stable.
