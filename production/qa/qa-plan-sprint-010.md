# QA Plan Sprint 010 - Kimi Vision And Evidence Foundation

Generated: 2026-06-21

## Scope

Sprint 010 validates the mocked Kimi multimodal request boundary and the local
Document -> Page -> Chunk -> Evidence foundation. It does not validate live Kimi
answers, full RAG retrieval, citation accuracy scoring, Web streaming, or
production readiness.

## Test Strategy

| Area | Required Evidence | Automated Test |
|---|---|---|
| Structured agent content | Provider-neutral content parts serialize without breaking string messages | `tests/unit/core/ports/test_agent_model_port.py` |
| Kimi Vision request shape | base64 images and `ms://<file_id>` are emitted as `image_url` parts | `tests/unit/infrastructure/test_kimi_client.py` |
| Kimi file Q&A request shape | extracted file content becomes a system message, not a raw file ID prompt | `tests/unit/infrastructure/test_kimi_client.py` |
| Page extraction | extracted text splits into page-like units; image metadata is captured | `tests/unit/test_page_extraction.py` |
| Parser failure safety | parser exceptions become visible page errors without crashing | `tests/unit/test_page_extraction.py` |
| Chunking | chunk IDs, page numbers, source hashes, and offsets are deterministic | `tests/unit/test_chunking_service.py` |
| Evidence repository | pages, chunks, and evidence records persist and round-trip | `tests/unit/test_evidence_repository.py` |
| Upload integration | registered files can trigger page/chunk extraction | `tests/unit/test_file_upload_service.py` |
| Runtime context | runs with `document_ids` include selected chunks in model context | `tests/integration/test_multimodal_chat.py` |

## Manual Smoke

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_file_upload_service.py tests/unit/test_chunking_service.py tests/unit/test_page_extraction.py tests/unit/test_evidence_repository.py tests/unit/core/ports/test_agent_model_port.py tests/unit/infrastructure/test_kimi_client.py tests/integration/test_multimodal_chat.py -q
```

Optional live Kimi smoke, only with operator approval and `MOONSHOT_API_KEY`:

```text
1. Upload a PNG chart through /v1/documents or CLI /attach.
2. Ask a vision question through the Kimi path.
3. Confirm the request uses either data:image/...;base64,... or ms://<file_id>.
4. Upload a PDF through Kimi Files and confirm extracted file content is placed
   in messages as context before asking document questions.
```

## Exit Criteria

- All automated tests above pass.
- No CI test requires live network or a real Kimi key.
- Parser support boundaries are documented.
- Stable remains forbidden in `docs/progress/runtime-maturity.yaml`.

## Remaining QA Gaps

- No live Kimi Vision/File Q&A smoke has been run.
- Local PDF text extraction depends on available extracted content or an injected parser; native PDF page parsing is not a hard dependency yet.
- Citation precision and claim-validation quality are not measured.
- Web, SDK reconnect, RAG, and industry-report gates remain future sprints.
