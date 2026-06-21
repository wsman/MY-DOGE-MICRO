# Sprint 009 - Kimi File Pipeline Foundation

> Stage: Release follow-up
> Duration: 2026-06-21 -> open
> Status: done with carryover
> Source roadmap: `C:\Users\Aby\.claude\plans\replicated-nibbling-pine.md`
> QA plan: `production/qa/qa-plan-sprint-009.md`

## Sprint Goal

Replace placeholder document handling with a real file pipeline that stores
hash/MIME/size/status metadata and lets CLI `/attach` pass real document IDs
into agent runs.

## Must Have

| ID | Task | Status | Acceptance Evidence |
|---|---|---|---|
| S009-001 | Document aggregate and repository metadata migration | done | `src/doge/core/domain/document_models.py`, `src/doge/core/ports/document_repository.py`, `tests/contract/test_agent_repositories.py` |
| S009-002 | File upload application service | done | `src/doge/application/services/file_upload_service.py`, `tests/unit/test_file_upload_service.py` |
| S009-003 | Kimi Files adapter boundary | done | `src/doge/infrastructure/llm/kimi_files_client.py`, `tests/unit/infrastructure/test_kimi_files_client.py` |
| S009-004 | `/v1/documents` multipart upload with JSON compatibility | done | `src/doge/interfaces/api/routers/v1/documents.py`, `tests/contract/test_v1_api.py` |
| S009-005 | CLI `/attach <path>` uses real file registration | done | `src/doge/interfaces/cli/commands/session.py`, `tests/cli/test_cli_session.py` |
| S009-006 | User docs and QA evidence | done | `docs/API.md`, `docs/CLI.md`, `docs/GETTING_STARTED.md`, `production/qa/qa-plan-sprint-009.md` |

## Should Have

| ID | Task | Status | Notes |
|---|---|---|---|
| S009-007 | Attached document content appears in full agent context evidence | carried to S010 | Implemented through Sprint 010 page/chunk/evidence context work. |

## Definition of Done

- [x] Real file upload persists file metadata.
- [x] Duplicate payloads are idempotent by hash.
- [x] CLI `/attach` no longer creates fake `doc-1` IDs.
- [x] Kimi Files adapter is isolated behind mocked tests.
- [x] API and CLI docs describe the new behavior.
- [x] Full suite green after broader regression.
- [ ] Remote CI green after push.
- [x] Carryover context grounding implemented in Sprint 010 local evidence chain.

## Verification

- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_file_upload_service.py tests/unit/infrastructure/test_kimi_files_client.py tests/contract/test_agent_repositories.py tests/contract/test_v1_api.py tests/cli/test_cli_session.py -q` -> `21 passed in 6.39s`.
- `.\.venv\Scripts\python.exe -m pytest tests/ -q` -> `791 passed, 5 skipped, 11 warnings in 55.22s`.

## Stable Declaration

Stable declaration remains forbidden. Sprint 009 plus Sprint 010 now close the
local file/context foundation, but full citation scoring, live Kimi smoke, Web
SSE, SDK reconnect, and release-quality gates remain open.
