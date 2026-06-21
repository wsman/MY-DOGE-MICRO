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

Status:
- Partial implementation landed on 2026-06-21.
- Real API multipart upload, file hash/MIME/size persistence, duplicate hash
  reuse, local parser fallback, and CLI `/attach <path>` registration are
  implemented.
- Sprint 010 adds local page/chunk extraction, upload-triggered extraction, and
  runtime context grounding for runs with `document_ids`.
- Still open before this blocker can be closed: final artifact/evidence proof
  with citations in a full user-visible agent run.

Scope:
- Replace `/attach` placeholder behavior with real file registration.
- Persist file hash, original filename, content type, size, and parsing status.
- Connect attached documents to agent context and artifact evidence.

Evidence required:
- CLI test proving `/attach <path>` persists a document record: `tests/cli/test_cli_session.py`.
- API or repository test proving file metadata and hash are stored:
  `tests/contract/test_v1_api.py`, `tests/contract/test_agent_repositories.py`,
  `tests/unit/test_file_upload_service.py`.
- Agent runtime test proving attached evidence is available to the context builder.
- User-facing runbook update: `docs/API.md`, `docs/CLI.md`, `docs/GETTING_STARTED.md`.

Candidate files:
- `src/doge/interfaces/cli/commands/session.py`
- `src/doge/interfaces/api/routers/v1/documents.py`
- `src/doge/application/agent/context_builder.py`
- `tests/cli/test_cli_session.py`
- `tests/integration/test_agent_sse_stream.py`

### F2 Evidence Extraction and Citation Grounding

Status:
- Partial implementation landed on 2026-06-21.
- `DocumentPage`, `DocumentChunk`, and `EvidenceRecord` domain models exist.
- SQLite page/chunk/evidence persistence and runtime chunk context are covered
  by local tests.
- Sprint 012 adds local RAG retrieval over evidence chunks and upgrades
  `lookup_evidence` to prefer source-backed chunks before notes fallback.
- Sprint 014 adds report-level claim records, citation records, citation
  assembly for generated industry reports, and a `generate_industry_report`
  agent tool.
- Still open: citation-quality evaluation and final end-to-end user-visible
  browser/demo artifact evidence.

Scope:
- Add source-backed evidence objects for uploaded or registered documents.
- Track citation snippets/pages where available.
- Reject or flag unsupported high-risk claims.

Evidence required:
- Unit tests for evidence extraction and citation serialization.
- Eval cases that expect grounded evidence flags.
- Artifact snapshot proving memo data includes citation/evidence references.

Candidate files:
- `src/doge/core/domain/page_models.py`
- `src/doge/core/domain/chunk_models.py`
- `src/doge/core/domain/evidence_models.py`
- `src/doge/application/agent/context_builder.py`
- `src/doge/application/agent/model_response_assembler.py`
- `src/doge/application/services/rag_service.py`
- `src/doge/infrastructure/database/evidence_repository.py`
- `src/doge/infrastructure/vector/sqlite_store.py`
- `tests/eval/cases.json`
- `tests/eval/test_run_eval.py`

### F3 Web Research Agent SSE Migration

Status:
- Partial implementation landed on 2026-06-21.
- Web Research Agent helper paths now consume v1 SSE for create and approval
  continuations instead of post-approval polling.
- Targeted Web tests cover create, approval, and store compatibility.
- Still open: browser/manual reconnect evidence against a running daemon and
  full Web test/build gate for Sprint 011.

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

Status:
- Partial implementation landed on 2026-06-21.
- TypeScript SDK stream reconnect/backoff preserves `Last-Event-ID`.
- Python sync SDK stream reconnect handles `httpx` transport failures.
- Python `AsyncDogeClient` supports async session creation, turn creation, and
  async SSE iteration.
- Still open: full SDK build gate, packaging/distribution documentation, and
  remote CI.

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
- `packages/doge-sdk-python/doge_sdk/session.py`
- `packages/doge-sdk-typescript/src/client.ts`
- `packages/doge-sdk-typescript/src/streaming.ts`
- `tests/contract/test_python_sdk.py`

### F5 Multimodal and Document Parsing Pipeline

Status:
- Partial implementation landed on 2026-06-21 for document lifecycle metadata
  and local parser fallback.
- Kimi Files API adapter exists with mocked tests.
- Sprint 010 adds provider-neutral structured content, Kimi Vision/file-Q&A
  serialization, image metadata pages, deterministic chunks, and safe parser
  failure handling.
- Still open: live Kimi Vision/File Q&A smoke, native local PDF/OCR coverage,
  and production-grade citation evaluation.

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
- `src/doge/application/services/page_extraction_service.py`
- `src/doge/infrastructure/llm/kimi_client.py`
- `docs/progress/document-parser-support-matrix.md`
- `tests/contract/test_v1_api.py`

### F6 Release-quality Operational Gates

Status:
- Partial implementation landed on 2026-06-21.
- Sprint 015 adds local performance smoke tests, Kimi chat retry/rate-limit
  behavior, Research Agent accessibility semantics, a Core Web Vitals
  non-applicability decision for the local loopback app, and a one-hour daemon
  soak protocol.
- Still open: executed soak evidence, remote CI after push, browser/manual
  reconnect evidence, live Kimi smoke, and citation-quality evaluation.

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
- `production/qa/performance-sprint-015.md`
- `production/qa/accessibility-sprint-015.md`
- `production/qa/soak-protocol-sprint-015.md`

## Recommended Sequencing

1. F1 real attach and persisted file metadata.
2. F2 evidence extraction and citation grounding.
3. F3 Web SSE migration.
4. F4 SDK reconnect and async support.
5. F5 multimodal/parser lifecycle.
6. F6 release-quality operational gates.

## Current Status

Status: follow-up in progress. Sprints 009-015 now provide local evidence for
real file upload, page/chunk/evidence storage, Kimi message serialization, Web
SSE helper usage, SDK reconnect/async streaming, local RAG, and deterministic
portfolio/risk/scenario tools, industry-report claim/citation assembly,
canonical scan-router decoupling from the legacy downloader, and local release
quality smoke evidence. Remaining blockers include live Kimi smoke,
citation-quality evaluation, browser/manual reconnect evidence, production
retrieval quality, real fundamentals/connectors, legacy compatibility deletion,
remote CI after push, and executed soak evidence. No level may be marked Stable.

This document satisfies the Sprint 008 requirement to give the remaining non-runtime blockers their own follow-up plan. It does not mark any level Stable.
