# QA Plan Sprint 009 - Real File Pipeline

Generated: 2026-06-21

## Scope

Sprint 009 validates the first Kimi-native demo foundation: real document file
registration, metadata persistence, CLI `/attach`, and the Kimi Files adapter
boundary. This plan does not validate multimodal visual reasoning, RAG,
citations, or Stable promotion.

## Test Strategy

| Area | Required Evidence | Automated Test |
|---|---|---|
| File upload service | SHA-256, MIME, size, storage path, parser status | `tests/unit/test_file_upload_service.py` |
| Duplicate upload handling | Same payload reuses existing document by hash | `tests/unit/test_file_upload_service.py` |
| Validation errors | Unsupported/empty/oversize files fail safely | `tests/unit/test_file_upload_service.py` |
| Kimi Files adapter | Upload/content calls are mocked, no live network in CI | `tests/unit/infrastructure/test_kimi_files_client.py` |
| SQLite repository | Metadata fields persist and hash lookup works | `tests/contract/test_agent_repositories.py` |
| API multipart route | `POST /v1/documents` accepts a real uploaded file | `tests/contract/test_v1_api.py` |
| API JSON compatibility | Existing SDK-style JSON registration still works | `tests/contract/test_v1_api.py` |
| CLI attach | `/attach <path>` registers a real file and passes `document_id` to runs | `tests/cli/test_cli_session.py` |

## Manual Smoke

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_file_upload_service.py tests/unit/infrastructure/test_kimi_files_client.py tests/contract/test_agent_repositories.py tests/contract/test_v1_api.py tests/cli/test_cli_session.py -q
```

Optional local API smoke:

```powershell
python -m uvicorn doge.interfaces.api.main:app --host 127.0.0.1 --port 8901
curl.exe -F "file=@demo_materials/market_summary_2026Q2.pdf" http://127.0.0.1:8901/v1/documents
```

Optional CLI smoke:

```text
doge session --title "File upload smoke"
doge session --resume ses-... --interactive
> /attach demo_materials/market_summary_2026Q2.pdf
```

## Exit Criteria

- All automated tests above pass.
- Uploaded documents expose `document_id`, `original_filename`, `file_hash`,
  `mime_type`, `size_bytes`, `storage_path`, `parsing_status`, `created_at`,
  and `updated_at`.
- API and CLI error paths return safe user-facing messages.
- No live Kimi call is required for CI.
- `docs/progress/runtime-stability-followup-plan.md` remains clear that Stable
  is still forbidden until the remaining gates pass.

## Remaining QA Gaps

- Full agent context grounding for attached files moved to Sprint 010 and now
  has local page/chunk/context tests.
- Citation scoring and claim-validation quality are not complete.
- Kimi Vision and file-based Q&A live smoke are not complete.
