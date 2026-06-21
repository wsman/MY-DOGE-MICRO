# Industry Report And Modular Migration Notes

Generated: 2026-06-21

## What Landed

- `GenerateIndustryReportUseCase` now orchestrates local RSRS ranking inputs,
  optional ticker fundamentals, local RAG research chunks, LLM synthesis with a
  deterministic Markdown fallback, claim extraction, evidence validation,
  citation assembly, and report persistence.
- Claim/citation data is represented by `ClaimRecord` and `CitationRecord`,
  persisted through `IClaimRepository` and `SQLiteClaimRepository`.
- `CitationService` assembles source labels, snippets, document IDs, pages, and
  chunk IDs from RAG/evidence result dictionaries.
- `ClaimValidationService` returns `supported` or `insufficient_evidence` for
  report claims based on text/numeric evidence overlap.
- The default agent tool registry includes `generate_industry_report`.
- The canonical scan router no longer imports the legacy TDX downloader for
  server lists or server download execution.
- TDX server listing/testing is behind `ITDXServerList` and
  `ConfigTDXServerList`.

## Evidence

- `tests/integration/test_industry_report.py`
- `tests/unit/test_claim_repository.py`
- `tests/unit/test_citation_service.py`
- `tests/unit/test_claim_validation.py`
- `tests/unit/infrastructure/test_tdx_server_list.py`
- `tests/contract/test_no_micro_imports_in_interface.py`
- `tests/unit/layer_gates/test_no_micro_under_doge.py`

Targeted local gate:

`.\.venv\Scripts\python.exe -m pytest tests/unit/test_citation_service.py tests/unit/test_claim_validation.py tests/unit/test_claim_repository.py tests/integration/test_industry_report.py tests/unit/infrastructure/test_tdx_server_list.py tests/contract/test_no_micro_imports_in_interface.py tests/unit/agent/test_tool_service.py tests/unit/agent/test_tool_registry.py tests/unit/application/contracts/test_dtos.py tests/test_api_routers.py::TestScanRouter tests/unit/interfaces/api/test_scan_local_fallback.py tests/test_tdx_adapter.py tests/unit/layer_gates/test_no_micro_under_doge.py tests/unit/layer_gates/test_api_layer_gate.py tests/unit/layer_gates/test_composition_root_location.py -q` -> `91 passed in 11.83s`.

## Boundaries Still Open

- Real fundamentals and announcement connectors are still provider/fixture work.
- Citation precision is not measured yet.
- Live Kimi synthesis and live TDX connectivity smoke remain
  operator-environment-dependent.
- Legacy TDX helper deletion remains a separate parity/deletion pass; S014 only
  removes direct canonical scan-router coupling.

## Maturity Impact

S014 improves the business workflow and modular boundary, but it does not allow a
Stable or Production Ready declaration.
