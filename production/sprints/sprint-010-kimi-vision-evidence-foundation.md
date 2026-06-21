# Sprint 010 - Kimi Vision And Evidence Foundation

> Stage: Release follow-up
> Duration: 2026-06-21 -> open
> Status: done with deferred live smoke
> Source roadmap: `C:\Users\Aby\.claude\plans\replicated-nibbling-pine.md`
> QA plan: `production/qa/qa-plan-sprint-010.md`

## Sprint Goal

Make Kimi-native visual/document input concrete at the adapter boundary and
create the first local evidence chain: Document -> Page -> Chunk -> Evidence.

## Must Have

| ID | Task | Status | Acceptance Evidence |
|---|---|---|---|
| S010-001 | Provider-neutral structured agent content parts | done | `src/doge/core/ports/agent_model.py`, `tests/unit/core/ports/test_agent_model_port.py` |
| S010-002 | Kimi message serialization for base64 image, `ms://<file_id>`, and extracted file text | done | `src/doge/infrastructure/llm/kimi_client.py`, `tests/unit/infrastructure/test_kimi_client.py` |
| S010-003 | Page extraction and deterministic chunking service | done | `src/doge/application/services/page_extraction_service.py`, `tests/unit/test_page_extraction.py`, `tests/unit/test_chunking_service.py` |
| S010-004 | SQLite page/chunk/evidence repository | done | `src/doge/infrastructure/database/evidence_repository.py`, `tests/unit/test_evidence_repository.py` |
| S010-005 | Runtime context builder includes selected document chunks safely | done | `src/doge/application/agent/context_builder.py`, `tests/integration/test_multimodal_chat.py` |
| S010-006 | Upload pipeline can trigger extraction after registration | done | `src/doge/application/services/file_upload_service.py`, `tests/unit/test_file_upload_service.py` |
| S010-007 | Parser support matrix and maturity/follow-up docs | done | `docs/progress/document-parser-support-matrix.md`, `docs/progress/runtime-maturity.yaml`, `docs/progress/runtime-stability-followup-plan.md` |

## Deferred

| ID | Task | Status | Notes |
|---|---|---|---|
| S010-008 | Live Kimi Vision/File Q&A smoke | deferred | Requires configured `MOONSHOT_API_KEY` and operator-controlled live network spend. Mocked adapter tests cover request shape in CI. |

## Definition of Done

- [x] Structured multimodal content is provider-neutral in the core port.
- [x] Kimi adapter serializes base64 images and uploaded file IDs into official Vision message shape.
- [x] Kimi file-based Q&A path places extracted file content into messages, not the file ID.
- [x] Documents can produce pages and chunks in SQLite from extracted text or deterministic local fallback.
- [x] Image uploads produce a page with metadata and a citeable chunk.
- [x] Evidence records persist and are queryable by run/document.
- [x] Runtime context can include selected chunks within a character budget.
- [ ] Live Kimi smoke evidence exists.
- [ ] Remote CI green after push.

## Verification

- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_file_upload_service.py tests/unit/test_chunking_service.py tests/unit/test_page_extraction.py tests/unit/test_evidence_repository.py tests/unit/core/ports/test_agent_model_port.py tests/unit/infrastructure/test_kimi_client.py tests/integration/test_multimodal_chat.py -q` -> `23 passed in 2.57s`.
- `.\.venv\Scripts\python.exe -m pytest tests/ -q` -> `803 passed, 5 skipped, 11 warnings in 57.41s`.

## Stable Declaration

Stable declaration remains forbidden. Sprint 010 only establishes the local
evidence/multimodal foundation; RAG retrieval, citation scoring, Web SSE, SDK
reconnect, financial industry tools, and release-quality gates remain open.
