# Document Parser Support Matrix

Generated: 2026-06-21

This matrix records the Sprint 009/010 parser behavior for the local
Kimi-native research demo. It is intentionally conservative: mocked tests prove
request shape and local persistence, while live Kimi behavior remains optional
operator smoke evidence.

| Input | Local Behavior | Kimi-Configured Behavior | Evidence |
|---|---|---|---|
| `.txt`, `.md`, `.csv`, `.json`, `.log` | UTF-8 text is read, split on form-feed page breaks, and chunked deterministically. | Same local content can still be sent as ordinary context. | `tests/unit/test_file_upload_service.py`, `tests/unit/test_page_extraction.py` |
| `.pdf` | If extracted text is already present on the `Document`, it is split into pages/chunks. Without a richer parser, local fallback stores a safe metadata snippet. | Kimi Files upload can retrieve extracted file content; file Q&A must place that extracted content into messages as a system prompt. | `tests/unit/test_page_extraction.py`, `tests/unit/infrastructure/test_kimi_files_client.py`, `tests/unit/infrastructure/test_kimi_client.py` |
| `.png`, `.jpg`, `.jpeg` | A page is created with image metadata; PNG/JPEG dimensions are read from file headers when possible. | Vision messages serialize to `data:image/...;base64,...` or `ms://<file_id>`. | `tests/unit/test_page_extraction.py`, `tests/unit/infrastructure/test_kimi_client.py` |
| Office formats | Metadata registration is supported; local text extraction is not guaranteed. | Kimi Files can provide extracted content when configured and available. | `tests/unit/test_file_upload_service.py`, `tests/unit/infrastructure/test_kimi_files_client.py` |
| Unsupported or failed parser input | Upload validation rejects unsupported suffixes; parser exceptions become visible `parser_error` page state. | Provider errors are captured as safe metadata/errors by the adapter boundary. | `tests/unit/test_file_upload_service.py`, `tests/unit/test_page_extraction.py` |

## Current Limitations

- Native local PDF page parsing is not a required dependency yet.
- OCR is only available through Kimi Files/Vision when configured.
- Evidence records exist, and local citation/numerical consistency scoring is
  implemented for comparable artifacts. Live citation-quality benchmarking is
  still open.
- No Stable or production-ready label may be inferred from this matrix.
